#!/usr/bin/env python3
"""
Hermes WebUI Session Indexer Daemon
====================================
Watches ALL Hermes profiles' state.dbs for new/updated TUI/CLI sessions
and automatically populates the WebUI's _index.json and sidecar files.

This ensures the WebUI sidebar always shows the same sessions as the
Hermes desktop app, even after a WebUI restart or Mac sleep/wake.

Designed after: ~/.hermes/skills/hermes-webui/webui-session-discovery/
  references/standalone-indexer-daemon-plan.md

Behaviour:
  - Polls every 15 seconds (configurable via DAEMON_POLL_INTERVAL env)
  - Uses cheap fingerprints (row_count + MAX(started_at) + SUM(message_count))
    to skip full processing when nothing has changed in a profile
  - Per-session change detection: only rewrites a sidecar when the session's
    message count changes (or the sidecar is missing)
  - Sidecar content: full stitched message history across the ancestor chain
    (root → ... → tip), so WebUI's "see older messages" scroll-back works
  - After each rebuild, deletes orphaned sidecar files whose session is no
    longer a chain tip (handles archived, deleted, or superseded sessions)
  - Supports all profiles (auto-discovers at startup)
  - Optionally nudges the WebUI HTTP server to warm its session cache
  - Atomic file writes (tmp + os.replace) to avoid corruption
  - Graceful shutdown on SIGTERM/SIGINT
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import signal
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────────
HERMES_HOME = Path.home() / ".hermes"
PROFILES_DIR = HERMES_HOME / "profiles"
WEBUI_SESSIONS_DIR = HERMES_HOME / "webui" / "sessions"
STATE_DB_ROOT = HERMES_HOME / "state.db"  # default profile
DAEMON_STATE_PATH = WEBUI_SESSIONS_DIR / "_daemon_state.json"
LOG_PATH = HERMES_HOME / "session-indexer.log"

POLL_INTERVAL = int(os.environ.get("DAEMON_POLL_INTERVAL", "15"))
WEBUI_URL = os.environ.get("HERMES_WEBUI_URL", "http://127.0.0.1:8787")
HEALTH_CHECK_TIMEOUT = 5  # seconds for HTTP health check

# Sources whose child sessions mark a parent as "no longer a chain tip".
# subagent children are excluded — they must NOT suppress their parent.
CONTINUATION_SOURCES = {"tui", "cli", "webui", "telegram"}

# ── Logging ─────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_PATH)),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("session-indexer")

# ── Signal handling ─────────────────────────────────────────────────────────────
_shutdown_requested = False


def _handle_shutdown(signum, frame):
    global _shutdown_requested
    log.info(f"Received signal {signum}, shutting down...")
    _shutdown_requested = True


signal.signal(signal.SIGTERM, _handle_shutdown)
signal.signal(signal.SIGINT, _handle_shutdown)


# ── Profile discovery ───────────────────────────────────────────────────────────
def discover_profiles() -> dict[str, Path]:
    """Return {profile_name: state_db_path} for all profiles with state.dbs.

    The default profile's state.db lives at ~/.hermes/state.db (root),
    NOT at ~/.hermes/profiles/default/state.db, even though a
    profiles/default/ dir may also exist.
    """
    profiles: dict[str, Path] = {}

    # Default profile — always at root state.db
    if STATE_DB_ROOT.exists():
        profiles["default"] = STATE_DB_ROOT

    # Named profiles
    if PROFILES_DIR.exists():
        for p in sorted(PROFILES_DIR.iterdir()):
            if not p.is_dir() or p.name == "default":
                continue
            db = p / "state.db"
            if db.exists():
                profiles[p.name] = db

    return profiles


# ── Fingerprint ─────────────────────────────────────────────────────────────────
def compute_fingerprint(db_path: Path) -> str | None:
    """Compute a cheap fingerprint for change detection.

    Includes COUNT, MAX(started_at), and SUM(message_count) so that
    both structural changes (new sessions, compressions) and message
    additions to existing tips are detected.

    Returns None if the DB can't be read (e.g. locked, missing).
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = 1")
        cur = conn.execute("""
            SELECT COUNT(*), COALESCE(MAX(started_at), 0), COALESCE(SUM(message_count), 0)
            FROM sessions
            WHERE message_count > 0
              AND title IS NOT NULL
              AND source IN ('tui', 'cli')
              AND (archived IS NULL OR archived = 0)
              AND id NOT IN (
                  SELECT DISTINCT parent_session_id FROM sessions
                  WHERE parent_session_id IS NOT NULL
                    AND source IN ('tui', 'cli', 'webui', 'telegram')
              )
        """)
        row = cur.fetchone()
        conn.close()
        raw = f"{row[0]}:{row[1]}:{row[2]}"
        return hashlib.md5(raw.encode()).hexdigest()
    except Exception as e:
        log.debug(f"Fingerprint failed for {db_path}: {e}")
        return None


# ── State.db queries ─────────────────────────────────────────────────────────────
def read_chain_tips(db_path: Path, profile_name: str) -> list[dict]:
    """Read all chain-tip sessions from a state.db.

    Chain tips = TUI/CLI sessions not referenced as a parent by any
    continuation session. This mirrors exactly what the Hermes desktop app shows.
    Subagent children are intentionally excluded from the NOT IN subquery so
    that a parent with only subagent children still appears as a chain tip.
    """
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT id, title, source, message_count, started_at, ended_at,
                   parent_session_id
            FROM sessions
            WHERE message_count > 0
              AND title IS NOT NULL
              AND source IN ('tui', 'cli')
              AND (archived IS NULL OR archived = 0)
              AND id NOT IN (
                  SELECT DISTINCT parent_session_id FROM sessions
                  WHERE parent_session_id IS NOT NULL
                    AND source IN ('tui', 'cli', 'webui', 'telegram')
              )
            ORDER BY started_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        log.warning(f"Could not read chain tips from {db_path}: {e}")
        return []


def read_chain_messages(db_path: Path, sid: str) -> list[dict]:
    """Read the full stitched message history for a chain-tip session.

    Walks the parent_session_id chain upward, following only parents whose
    end_reason is 'compression' or 'cli_close' (these are the sessions the
    Hermes CLI compressed/closed to start this continuation). Produces a flat
    list ordered root → ... → tip, which is exactly what the WebUI stores in
    sidecar files to enable the "see older messages" scroll-back feature.

    Uses stitch logic equivalent to get_cli_session_messages(stitch_continuations=True)
    in the WebUI backend.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = 1")
        conn.row_factory = sqlite3.Row

        # Build the ancestor chain: [oldest_ancestor, ..., parent, sid]
        chain = [sid]
        current_id = sid
        seen = {current_id}

        for _ in range(20):  # max 20 hops up the chain
            current_row = conn.execute(
                "SELECT parent_session_id FROM sessions WHERE id=?",
                (current_id,)
            ).fetchone()
            if not current_row:
                break
            parent_id = current_row["parent_session_id"]
            if not parent_id or parent_id in seen:
                break
            # Only follow a parent if the parent itself ended via compression/cli_close
            # (meaning the current session is its direct continuation)
            parent_row = conn.execute(
                "SELECT end_reason FROM sessions WHERE id=?",
                (parent_id,)
            ).fetchone()
            if not parent_row:
                break
            if parent_row["end_reason"] not in ("compression", "cli_close"):
                break
            chain.insert(0, parent_id)
            seen.add(parent_id)
            current_id = parent_id

        # Fetch all messages across the chain in chronological order
        placeholders = ",".join("?" * len(chain))
        rows = conn.execute(f"""
            SELECT role, content, timestamp
            FROM messages
            WHERE session_id IN ({placeholders})
            ORDER BY timestamp ASC, id ASC
        """, chain).fetchall()

        conn.close()
        return [
            {"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in rows
        ]
    except Exception as e:
        log.warning(f"Could not read chain messages for {sid} in {db_path}: {e}")
        return []


# ── Index file operations ───────────────────────────────────────────────────────
def load_index() -> list[dict]:
    """Load _index.json, returning a list of session entries."""
    index_path = WEBUI_SESSIONS_DIR / "_index.json"
    if not index_path.exists():
        return []
    try:
        raw = json.loads(index_path.read_text())
        if isinstance(raw, list):
            return raw
        for key in ("sessions", "items", "entries"):
            if key in raw:
                return raw[key]
        return []
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Failed to read _index.json: {e}")
        return []


def save_index(items: list[dict]) -> bool:
    """Atomically write _index.json. Returns True on success."""
    WEBUI_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = WEBUI_SESSIONS_DIR / "_index.json.tmp"
    final_path = WEBUI_SESSIONS_DIR / "_index.json"
    try:
        tmp_path.write_text(json.dumps(items, indent=2))
        tmp_path.replace(final_path)
        return True
    except OSError as e:
        log.error(f"Failed to write _index.json: {e}")
        return False


# ── Sidecar file operations ─────────────────────────────────────────────────────
def make_sidecar(row: dict, messages: list[dict]) -> dict:
    """Build a sidecar dict from a state.db row with full message content.

    The messages list should be the full stitched chain history (root → tip)
    so that the WebUI's 'see older messages' scroll-back works correctly.
    """
    ts_updated = row.get("ended_at") or row.get("started_at") or 0
    return {
        "session_id": row["id"],
        "title": row.get("title"),
        "created_at": row.get("started_at"),
        "updated_at": ts_updated,
        "parent_session_id": row.get("parent_session_id"),
        "message_count": len(messages),
        "is_cli_session": True,
        "source_tag": row.get("source") or "tui",
        "raw_source": row.get("source") or "tui",
        "session_source": "cli",
        "source_label": "TUI",
        "read_only": False,
        "pinned": False,
        "archived": False,
        "active_stream_id": None,
        "pending_user_message": None,
        "pending_attachments": [],
        "messages": messages,
        "tool_calls": [],
        "context_messages": [],
        "_recovered_from_state_db": True,
        "_recovered_at": datetime.now(timezone.utc).isoformat(),
    }


def write_sidecar(session_id: str, sidecar: dict) -> bool:
    """Write a sidecar file for one session. Returns True on success."""
    path = WEBUI_SESSIONS_DIR / f"{session_id}.json"
    tmp_path = WEBUI_SESSIONS_DIR / f"{session_id}.json.tmp"
    try:
        tmp_path.write_text(json.dumps(sidecar, indent=2))
        tmp_path.replace(path)
        return True
    except OSError as e:
        log.error(f"Failed to write sidecar {session_id}: {e}")
        return False


def cleanup_orphaned_sidecars(current_tip_ids: set[str]) -> int:
    """Delete sidecar files on disk that are NOT in the current chain-tip index.

    This handles archived sessions, deleted sessions, and sessions superseded
    by a continuation — their stale sidecars would otherwise remain on disk
    and appear in the WebUI sidebar (since WebUI globs all *.json files).

    Skips files whose names begin with '_' (index, daemon state, tmp files).
    Returns the number of files deleted.
    """
    deleted = 0
    for f in list(WEBUI_SESSIONS_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        if f.stem not in current_tip_ids:
            try:
                f.unlink()
                log.info(f"  Deleted orphaned sidecar: {f.name}")
                deleted += 1
            except OSError as e:
                log.warning(f"  Could not delete orphaned sidecar {f.name}: {e}")
    return deleted


# ── Daemon state (persistent fingerprints + per-session message counts) ──────────
def load_daemon_state() -> dict:
    """Load the daemon's own persistent state."""
    if not DAEMON_STATE_PATH.exists():
        return {"profiles": {}, "session_msg_counts": {}, "version": 2}
    try:
        state = json.loads(DAEMON_STATE_PATH.read_text())
        # Migrate v1 state (no session_msg_counts)
        if "session_msg_counts" not in state:
            state["session_msg_counts"] = {}
        return state
    except (json.JSONDecodeError, OSError):
        return {"profiles": {}, "session_msg_counts": {}, "version": 2}


def save_daemon_state(state: dict) -> None:
    """Atomically save daemon state."""
    DAEMON_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DAEMON_STATE_PATH.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(state, indent=2))
        tmp.replace(DAEMON_STATE_PATH)
    except OSError as e:
        log.warning(f"Failed to save daemon state: {e}")


# ── WebUI nudge ─────────────────────────────────────────────────────────────────
def nudge_webui() -> bool:
    """Optionally warm the WebUI's session cache by hitting its sessions endpoint.

    Returns True if the WebUI responded healthily.
    """
    try:
        req = urllib.request.Request(
            f"{WEBUI_URL}/api/sessions",
            method="GET",
            headers={"User-Agent": "Hermes-Session-Indexer/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=HEALTH_CHECK_TIMEOUT)
        return resp.status == 200
    except (urllib.error.URLError, OSError) as e:
        log.debug(f"WebUI nudge failed (WebUI may be offline): {e}")
        return False


# ── Core logic ──────────────────────────────────────────────────────────────────
def process_profile(
    profile_name: str,
    db_path: Path,
    index_by_id: dict[str, dict],
    session_msg_counts: dict[str, int],
) -> int:
    """Process one profile: sync all chain-tip sessions to index + sidecars.

    For each chain-tip session:
      - Checks if the sidecar is missing or its message count has changed
      - If so: reads the full stitched message history and rewrites the sidecar
      - Always adds the session to the index (index is rebuilt from scratch each cycle)

    Returns the number of sidecars written this cycle.
    """
    rows = read_chain_tips(db_path, profile_name)
    sidecars_written = 0

    for row in rows:
        sid = row["id"]
        db_msg_count = row.get("message_count", 0)
        sidecar_path = WEBUI_SESSIONS_DIR / f"{sid}.json"

        # Change detection: rewrite sidecar only when needed
        sidecar_exists = sidecar_path.exists()
        stored_count = session_msg_counts.get(sid)
        needs_write = (
            not sidecar_exists
            or stored_count is None
            or stored_count != db_msg_count
        )

        if needs_write:
            messages = read_chain_messages(db_path, sid)
            sidecar = make_sidecar(row, messages)
            if write_sidecar(sid, sidecar):
                sidecars_written += 1
                session_msg_counts[sid] = db_msg_count
                log.info(
                    f"  [{profile_name}] Wrote sidecar {sid} "
                    f"({len(messages)} stitched msgs, db_count={db_msg_count})"
                )

        # Always build a fresh index entry for this chain tip
        ts = row.get("ended_at") or row.get("started_at") or 0
        entry = {
            "session_id": sid,
            "title": row.get("title"),
            "created_at": row.get("started_at"),
            "updated_at": ts,
            "parent_session_id": row.get("parent_session_id"),
            "message_count": db_msg_count,
            "is_cli_session": True,
            "source_tag": row.get("source") or "tui",
            "profile": profile_name,
            "pinned": False,
            "archived": False,
        }
        index_by_id[sid] = entry

    return sidecars_written


def poll_once(
    profiles: dict[str, Path],
    daemon_state: dict,
) -> tuple[bool, int, int]:
    """Run one poll cycle — rebuild the WebUI index from scratch.

    Each cycle:
      1. Reads chain-tip sessions from every profile
      2. Writes/updates sidecars with full stitched messages (change-detected)
      3. Writes a complete fresh _index.json
      4. Deletes orphaned sidecar files not in the current index
      5. Prunes stale per-session counts from daemon state

    Returns (changed, total_index_entries, total_sidecars_written).
    """
    index_by_id: dict[str, dict] = {}
    session_msg_counts: dict[str, int] = daemon_state.setdefault("session_msg_counts", {})
    profiles_seen: dict[str, str] = daemon_state.setdefault("profiles", {})
    total_sidecars = 0
    changed = False

    for profile_name, db_path in sorted(profiles.items()):
        fp = compute_fingerprint(db_path)
        old_fp = profiles_seen.get(profile_name)
        profile_changed = fp is not None and fp != old_fp

        sidecars = process_profile(
            profile_name, db_path, index_by_id, session_msg_counts,
        )
        total_sidecars += sidecars

        if fp is not None:
            profiles_seen[profile_name] = fp

        if profile_changed or sidecars > 0:
            changed = True
            log.info(
                f"  [{profile_name}] fingerprint={'changed' if profile_changed else 'same'}, "
                f"{sidecars} sidecar(s) updated"
            )

    # Always save the complete rebuilt index (cheap, ensures consistency)
    current_tip_ids = set(index_by_id.keys())
    old_ids = {e.get("session_id") for e in load_index()}
    if current_tip_ids != old_ids or changed:
        changed = True
        if save_index(list(index_by_id.values())):
            log.info(
                f"Rebuilt _index.json: {len(index_by_id)} entries "
                f"across {len(profiles)} profile(s)"
            )
        else:
            log.error("Failed to save rebuilt _index.json")

    # Remove orphaned sidecar files (not in current chain-tip set)
    deleted = cleanup_orphaned_sidecars(current_tip_ids)
    if deleted > 0:
        log.info(f"Cleaned up {deleted} orphaned sidecar(s)")
        changed = True

    # Prune session_msg_counts for sessions no longer in the chain-tip set
    stale = [k for k in list(session_msg_counts.keys()) if k not in current_tip_ids]
    for k in stale:
        del session_msg_counts[k]
    if stale:
        log.debug(f"Pruned {len(stale)} stale session count(s) from daemon state")

    save_daemon_state(daemon_state)
    return changed, len(index_by_id), total_sidecars


# ── Main loop ───────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("Hermes Session Indexer Daemon starting")
    log.info(f"Poll interval: {POLL_INTERVAL}s")
    log.info(f"WebUI URL: {WEBUI_URL}")
    log.info(f"WebUI sessions dir: {WEBUI_SESSIONS_DIR}")

    # Auto-discover profiles
    profiles = discover_profiles()
    if not profiles:
        log.warning("No state.dbs found! Nothing to index.")
        log.info(f"  Checked root: {STATE_DB_ROOT}")
        log.info(f"  Checked profiles: {PROFILES_DIR}/*/")
        log.info("Will retry on next poll cycle...")

    log.info(f"Discovered {len(profiles)} profile(s): {list(profiles.keys())}")
    for name, path in profiles.items():
        size = path.stat().st_size
        log.info(f"  {name}: {path} ({size:,} bytes)")

    # Load daemon state
    daemon_state = load_daemon_state()
    log.info(
        f"Loaded daemon state: {len(daemon_state.get('profiles', {}))} tracked profiles, "
        f"{len(daemon_state.get('session_msg_counts', {}))} cached message counts"
    )

    # Bootstrap: do an immediate run
    log.info("Running initial poll...")
    changed, entries, sidecars = poll_once(profiles, daemon_state)
    if changed:
        log.info(f"Initial poll: {entries} index entries, {sidecars} sidecars written")
        nudge_webui()
    else:
        log.info("Initial poll: everything up to date")

    # Main poll loop
    tick = 0
    while not _shutdown_requested:
        time.sleep(POLL_INTERVAL)
        tick += 1
        try:
            changed, entries, sidecars = poll_once(profiles, daemon_state)
            if changed:
                log.info(f"Poll #{tick}: {entries} index entries, {sidecars} sidecars written")
                nudge_webui()

            # Re-discover profiles periodically (every 60 ticks = ~15 min)
            if tick % 60 == 0:
                old_count = len(profiles)
                profiles = discover_profiles()
                if len(profiles) != old_count:
                    log.info(f"Profile list changed: {list(profiles.keys())}")
        except Exception as e:
            log.error(f"Poll #{tick} failed: {e}", exc_info=True)

    log.info("Shutdown complete. Goodbye.")


if __name__ == "__main__":
    main()
