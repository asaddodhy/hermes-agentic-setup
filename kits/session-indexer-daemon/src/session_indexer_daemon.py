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
  - Uses cheap fingerprints (row_count + MAX(started_at)) to avoid I/O
  - Writes new chain-tip sessions to _index.json + sidecar files
  - Sets pre_compression_snapshot=true on chain parents
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

CLI_SOURCES = {"tui", "cli"}  # sources we care about

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

    Returns None if the DB can't be read (e.g. locked, missing).
    Uses row_count + MAX(started_at) for sessions matching the chain-tip filter.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only = 1")
        cur = conn.execute("""
            SELECT COUNT(*), COALESCE(MAX(started_at), 0)
            FROM sessions
            WHERE message_count > 0
              AND title IS NOT NULL
              AND (source IN ('tui', 'cli') OR source IS NULL)
              AND (archived IS NULL OR archived = 0)
              AND id NOT IN (
                  SELECT DISTINCT parent_session_id FROM sessions
                  WHERE parent_session_id IS NOT NULL
                    AND source IN ('tui', 'cli', 'webui', 'telegram')
              )
        """)
        row = cur.fetchone()
        conn.close()
        raw = f"{row[0]}:{row[1]}"
        return hashlib.md5(raw.encode()).hexdigest()
    except Exception as e:
        log.debug(f"Fingerprint failed for {db_path}: {e}")
        return None


# ── State.db query ──────────────────────────────────────────────────────────────
def read_chain_tips(db_path: Path, profile_name: str) -> list[dict]:
    """Read all chain-tip sessions from a state.db.

    Chain tips = sessions not referenced as a parent by any other session.
    This mirrors exactly what the Hermes desktop app shows.
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
              AND (source IN ('tui', 'cli') OR source IS NULL)
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
        # Handle wrapped format (unlikely but safe)
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
def load_template_sidecar() -> dict | None:
    """Load an existing sidecar as a structural template for new ones."""
    for f in sorted(WEBUI_SESSIONS_DIR.glob("*.json")):
        if f.name in ("_index.json", "_index.json.tmp", "_daemon_state.json"):
            continue
        try:
            s = json.loads(f.read_text())
            if isinstance(s, dict) and "session_id" in s:
                return s
        except Exception:
            continue
    return None


def make_sidecar(row: dict, template: dict | None = None) -> dict:
    """Build a minimal sidecar dict from a state.db row."""
    sidecar = dict(template) if template else {}
    ts_updated = row.get("ended_at") or row.get("started_at") or 0

    sidecar.update({
        "session_id": row["id"],
        "title": row.get("title"),
        "created_at": row.get("started_at"),
        "updated_at": ts_updated,
        "parent_session_id": row.get("parent_session_id"),
        "message_count": row.get("message_count", 0),
        "is_cli_session": True,
        "source_tag": row.get("source") or "tui",
        "raw_source": row.get("source") or "tui",
        "session_source": "cli",
        "source_label": "TUI",
        "pinned": False,
        "archived": False,
        "active_stream_id": None,
        "pending_user_message": None,
        "pending_attachments": [],
        "messages": [],
        "tool_calls": [],
        "context_messages": [],
        "_recovered_from_state_db": True,
        "_recovered_at": datetime.now(timezone.utc).isoformat(),
    })
    return sidecar


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


# ── Daemon state (persistent fingerprints) ──────────────────────────────────────
def load_daemon_state() -> dict:
    """Load the daemon's own watermark state."""
    if not DAEMON_STATE_PATH.exists():
        return {"profiles": {}, "version": 1}
    try:
        return json.loads(DAEMON_STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {"profiles": {}, "version": 1}


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
    existing_sidecars: set[str],
    template: dict | None,
) -> tuple[list[dict], int]:
    """Process one profile: find new sessions, create sidecars & index entries.

    Returns (new_index_entries, sidecars_written_count).
    """
    rows = read_chain_tips(db_path, profile_name)
    new_entries: list[dict] = []
    sidecars_written = 0

    for row in rows:
        sid = row["id"]

        # Already in index → skip
        if sid in index_by_id:
            continue

        # Write sidecar if missing
        if sid not in existing_sidecars:
            sidecar = make_sidecar(row, template)
            if write_sidecar(sid, sidecar):
                sidecars_written += 1
                existing_sidecars.add(sid)
            else:
                continue

        # Build index entry
        ts = row.get("ended_at") or row.get("started_at") or 0
        entry = {
            "session_id": sid,
            "title": row.get("title"),
            "created_at": row.get("started_at"),
            "updated_at": ts,
            "parent_session_id": row.get("parent_session_id"),
            "message_count": row.get("message_count", 0),
            "is_cli_session": True,
            "source_tag": row.get("source") or "tui",
            "profile": profile_name,
            "pinned": False,
            "archived": False,
        }
        new_entries.append(entry)
        index_by_id[sid] = entry

        # Set pre_compression_snapshot on parent if it exists in the index
        parent_id = row.get("parent_session_id")
        if parent_id and parent_id in index_by_id:
            parent_entry = index_by_id[parent_id]
            if not parent_entry.get("pre_compression_snapshot"):
                parent_entry["pre_compression_snapshot"] = True
                log.info(f"  Set pre_compression_snapshot=true on parent {parent_id}")

    return new_entries, sidecars_written


def poll_once(
    profiles: dict[str, Path],
    daemon_state: dict,
) -> tuple[bool, int, int]:
    """Run one poll cycle — rebuild the WebUI index from scratch.

    Each cycle reads chain-tip sessions from every profile and writes
    the complete _index.json, so superseded chain tips are automatically
    removed.  Sidecar files for sessions that still exist are kept;
    orphaned sidecars can be cleaned separately.

    Returns (changed, total_index_entries, total_sidecars_written).
    """
    # Rebuild index from scratch every cycle
    index_by_id: dict[str, dict] = {}

    existing_sidecars = {
        f.stem for f in WEBUI_SESSIONS_DIR.glob("*.json")
        if f.name not in ("_index.json", "_index.json.tmp", "_daemon_state.json")
    }

    template = load_template_sidecar()
    total_sidecars = 0
    profiles_seen = daemon_state.setdefault("profiles", {})
    changed = False

    for profile_name, db_path in sorted(profiles.items()):
        # Read chain tips and add all of them to the fresh index
        new_entries, sidecars = process_profile(
            profile_name, db_path, index_by_id, existing_sidecars, template,
        )

        total_sidecars += sidecars

        # Track fingerprint for diagnostics (no longer used for skip)
        fp = compute_fingerprint(db_path)
        if fp is not None:
            profiles_seen[profile_name] = fp

        if new_entries or sidecars > 0:
            changed = True
            log.info(
                f"  {profile_name}: +{len(new_entries)} index entries, "
                f"+{sidecars} sidecars"
            )

    # Save the complete rebuilt index (not an append)
    if changed:
        if save_index(list(index_by_id.values())):
            log.info(
                f"Rebuilt _index.json with {len(index_by_id)} entries "
                f"from {len(profiles)} profile(s)"
            )
        else:
            log.error("Failed to save rebuilt _index.json")

    # Save daemon state (fingerprints)
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
    log.info(f"Loaded daemon state with {len(daemon_state.get('profiles', {}))} tracked profiles")

    # Bootstrap: do an immediate run
    log.info("Running initial poll...")
    changed, entries, sidecars = poll_once(profiles, daemon_state)
    if changed:
        log.info(f"Initial poll: +{entries} index entries, +{sidecars} sidecars")
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
                log.info(f"Poll #{tick}: +{entries} index entries, +{sidecars} sidecars")
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
