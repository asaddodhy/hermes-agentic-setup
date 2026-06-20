---
name: session-indexer-daemon
description: "Bridges Hermes CLI/TUI sessions from state.db into the WebUI session index — polls every 15s, writes only chain-tip sessions, rebuilds the index from scratch each cycle, cleans up orphaned sidecars automatically."
version: 2.0.0
author: dodhya
models:
  primary: any
services:
  launchd:
    required: true
    description: "Runs the Python daemon as a user-level launchd service (ai.hermes.session-indexer)"
    setup: "Copy the plist to ~/Library/LaunchAgents/ and load with launchctl"
parameters:
  DAEMON_POLL_INTERVAL:
    description: "Seconds between poll cycles (default: 15)"
    default: 15
  HERMES_WEBUI_URL:
    description: "Base URL of the Hermes WebUI HTTP server"
    default: "http://127.0.0.1:8787"
environment:
  os: [macos]
  hermes_version: ">=0.1.0"
dependencies:
  - hermes-install
  - hermes-webui
security:
  secrets_stored: []
  trust_boundaries:
    - "Runs as the logged-in user via launchd (gui/$UID)"
  known_threats:
    - "Daemon writes to ~/.hermes/webui/sessions/ — same dir as the WebUI. No cross-user exposure."
tags: [sessions, webui, daemon, sync, chain-tip, sidecar]
src:
  fileManifest:
    - src/session_indexer_daemon.py
    - src/ai.hermes.session-indexer.plist
---

# Session Indexer Daemon

## Goal

Keep the Hermes WebUI session index (`_index.json`) and sidecar files in sync with the CLI/desktop app's sessions — showing only **chain-tip sessions** (the latest session in each continuation chain), with full stitched message history so the WebUI's "see older messages" scroll-back works correctly.

## When to Use

- After installing the Hermes WebUI and you want the session list to match the desktop app
- Sessions that have been continued (compressed) keep showing up in the WebUI
- WebUI shows "Session not available" when you click a CLI session
- Extra/stale sessions appear in the WebUI sidebar that are not in the desktop app
- A fresh machine setup where the WebUI session list is empty or stale
- After Mac sleep/wake cycles where the WebUI lost track of sessions

## How It Works

```
┌──────────────┐     polls every 15s     ┌──────────────────────┐
│  Hermes       │ ◄────────────────────── │  session_indexer     │
│  state.db     │     reads chain tips     │  _daemon.py          │
│  (all profs)  │ ──────────────────────► │                      │
└──────────────┘                          │  launchd service     │
                                          │  ai.hermes.session-  │
                                          │  indexer             │
                                          │                      │
                                          │  writes              │
                                          │  _index.json         │
                                          │  + sidecar .json     │
                                          │  (with messages)     │
                                          │                      │
                                          │  deletes orphaned    │
                                          │  sidecars            │
                                          └──────────┬───────────┘
                                                     │
                                                     ▼
                                          ┌──────────────────────┐
                                          │  ~/.hermes/webui/    │
                                          │  sessions/            │
                                          │   _index.json         │
                                          │   *.json (sidecars)   │
                                          └──────────────────────┘
```

Each poll cycle the daemon:

1. **Discovers all Hermes profiles** — `~/.hermes/state.db` (default) and `~/.hermes/profiles/*/state.db` (named profiles)
2. **Queries chain tips per profile** — sessions not referenced as a parent by any continuation session; subagent children excluded
3. **Change-detected sidecar sync** — reads per-session message count from state.db; only rewrites a sidecar when the count has changed or the file is missing
4. **Full stitched message history** — walks the `parent_session_id` chain up to the root, concatenates all ancestor messages so the WebUI's "see older messages" scroll-back works
5. **Rebuilds `_index.json` from scratch** — no stale accumulation; superseded chain tips automatically disappear
6. **Cleans orphaned sidecars** — deletes any `*.json` sidecar whose session is no longer a chain tip; prevents archived/deleted/superseded sessions appearing in the sidebar
7. **Nudges the WebUI** to warm its session cache

## Architecture Notes

### Why sidecars need full stitched messages

The WebUI's "see older messages" button does NOT navigate to a different session — it expands `msg_limit` within the same session's flat message list. The sidecar for a chain-tip session must contain ALL messages from the entire ancestor chain (root → ... → tip), concatenated in timestamp order. Without this, "see older messages" only scrolls within the current segment.

The daemon reads the full stitched history using `read_chain_messages()` which walks `parent_session_id` upward following `compression`/`cli_close` end reasons.

### Why orphan cleanup is critical

The WebUI globs ALL `*.json` files in `~/.hermes/webui/sessions/` — not just entries in `_index.json`. Without cleanup, sidecars for archived sessions, deleted sessions, or sessions superseded by a continuation remain on disk and appear in the WebUI sidebar even after the desktop app has removed them.

### Sidecar vs state.db

Sidecars are a **WebUI-only display cache**. The Hermes backend never reads them — it always uses `state.db`. Deleting a sidecar does NOT affect any conversation history; it only affects WebUI rendering. The daemon can safely recreate any sidecar from state.db at any time.

### Change detection layers

| Layer | What changes | What triggers a rewrite |
|---|---|---|
| **Profile fingerprint** | MD5(COUNT + MAX(started_at) + SUM(message_count)) | Any new session or message addition |
| **Per-session count** | `session_msg_counts[sid]` in daemon state | When count in state.db ≠ stored count |
| **Sidecar missing** | File absent from disk | Always triggers a write |

## Setup

### Prerequisites

| Item | Required | Notes |
|------|----------|-------|
| Hermes installed | Yes | Provides the `~/.hermes/` structure |
| Hermes WebUI running | Yes | The daemon writes to `~/.hermes/webui/sessions/` |
| Python 3.11+ | Yes | Comes with Hermes venv at `~/.hermes/hermes-agent/venv/bin/python3` |

### What gets installed

| File | Destination | Purpose |
|------|-------------|---------|
| `session_indexer_daemon.py` | `~/.hermes/bin/session_indexer_daemon.py` | The polling daemon script |
| `ai.hermes.session-indexer.plist` | `~/Library/LaunchAgents/ai.hermes.session-indexer.plist` | launchd service definition |

## Steps

### Step 1 — Deploy the daemon script

```bash
cp kits/session-indexer-daemon/src/session_indexer_daemon.py ~/.hermes/bin/
chmod +x ~/.hermes/bin/session_indexer_daemon.py
```

### Step 2 — Deploy and load the launchd plist

The plist contains hardcoded paths with `__YOUR_USERNAME__` — replace with your actual macOS username:

```bash
# Replace placeholder with your username
sed "s/__YOUR_USERNAME__/$(whoami)/g" \
  kits/session-indexer-daemon/src/ai.hermes.session-indexer.plist \
  > ~/Library/LaunchAgents/ai.hermes.session-indexer.plist

# Load the service
launchctl load ~/Library/LaunchAgents/ai.hermes.session-indexer.plist
```

> **Note:** Launchd plist paths are literal XML — `~` and `${HOME}` are NOT expanded. You must hardcode `/Users/<username>/...`.

### Step 3 — Clear any stale daemon state

If migrating from v1, delete the old daemon state to force a clean initial sync:

```bash
rm -f ~/.hermes/webui/sessions/_daemon_state.json
```

### Step 4 — Verify the daemon is running

```bash
# Check process
launchctl list ai.hermes.session-indexer

# Check log
tail -10 ~/.hermes/session-indexer.log
```

Expected output on first run:

```
[INFO] Deleted orphaned sidecar: <old_session>.json
[INFO] Cleaned up N orphaned sidecar(s)
[INFO] [default] Wrote sidecar <sid> (557 stitched msgs, db_count=203)
[INFO] Rebuilt _index.json: 22 entries across 3 profile(s)
[INFO] Initial poll: 22 index entries, 22 sidecars written
```

### Step 5 — Check the WebUI session list

Open the WebUI in your browser and verify:
- Session list matches the desktop app (chain tips only)
- Clicking a session shows the full conversation
- "See older messages" scrolls all the way back to the root session

### Restarting after updates

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.session-indexer
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DAEMON_POLL_INTERVAL` | `15` | Seconds between poll cycles |
| `HERMES_WEBUI_URL` | `http://127.0.0.1:8787` | WebUI HTTP server URL |

## Constraints

- **macOS only** — relies on launchd. On Linux, use a systemd user service
- **Python 3.11+** — the Hermes venv provides this
- **WebUI must be running** — the daemon writes to the sessions directory the WebUI reads from
- **Sidecar files are large** — each sidecar contains the full stitched message history for its chain. For very long conversation chains this can be several MB per session

## Chain-Tip SQL

```sql
-- A session is a chain tip if it is a TUI/CLI session with no continuation children
SELECT id, title, source, message_count
FROM sessions
WHERE message_count > 0
  AND title IS NOT NULL
  AND source IN ('tui', 'cli')                               -- only CLI/TUI sessions
  AND (archived IS NULL OR archived = 0)                     -- not archived
  AND id NOT IN (
      SELECT DISTINCT parent_session_id FROM sessions
      WHERE parent_session_id IS NOT NULL
        AND source IN ('tui', 'cli', 'webui', 'telegram')    -- continuation child types
      -- NOTE: 'subagent' intentionally excluded — subagent children are task spawns,
      -- not user continuations; they must NOT suppress their parent
  )
```

## Verification Checklist

- [ ] Daemon script deployed: `ls -la ~/.hermes/bin/session_indexer_daemon.py`
- [ ] Launchd plist deployed: `ls -la ~/Library/LaunchAgents/ai.hermes.session-indexer.plist`
- [ ] Daemon running: `launchctl list ai.hermes.session-indexer` shows a PID
- [ ] Daemon polling: `tail -3 ~/.hermes/session-indexer.log` shows recent poll entries
- [ ] Index populated: `cat ~/.hermes/webui/sessions/_index.json | python3 -m json.tool | grep session_id | wc -l`
- [ ] Sidecars have messages: `python3 -c "import json,pathlib; s=pathlib.Path.home()/'.hermes/webui/sessions'; f=next(x for x in s.glob('*.json') if not x.name.startswith('_')); d=json.loads(f.read_text()); print(f'{f.name}: {len(d.get(\"messages\",[]))} messages')"`
- [ ] WebUI shows correct sessions: Open WebUI — only chain tips, no archived/deleted sessions
- [ ] "See older messages" works: Click a continued session, scroll up, click "see older messages"

## Failures Overcome

### Bug 1: Source filter too narrow (v1.0)

The original child-exclusion subquery only checked for `tui`/`cli` children, so a TUI parent with WebUI-only children was incorrectly treated as a chain tip.

**Fix:** Added `'webui'` and `'telegram'` to the continuation source list. Removed the `OR source IS NULL` catch-all (zero NULL-source children existed in practice).

### Bug 2: Append-only index (v1.0)

The daemon only appended new chain tips to `_index.json` — it never removed superseded entries. After multiple continuations in the same chain, the index accumulated every intermediate tip.

**Fix:** Rebuilt `_index.json` from scratch each cycle using only current chain tips.

### Bug 3: Empty sidecar messages (v1.0)

The daemon wrote `"messages": []` in every sidecar. The WebUI requires real messages to render a session — an empty `messages` array causes "Session not available" which then deletes the sidecar on save, causing the session to disappear from the sidebar on the next poll.

**Fix (v2.0):** `make_sidecar()` now calls `read_chain_messages()` which reads the full stitched message history from state.db (walking the ancestor chain) and populates `messages` with real content.

### Bug 4: Orphaned sidecars from archived/deleted sessions (v1.0)

The WebUI globs ALL `*.json` files in the sessions directory, not just entries in `_index.json`. Old sidecar files for archived sessions, deleted sessions, and sessions from all profiles accumulated and appeared in the WebUI sidebar even though they were absent from the desktop app.

**Fix (v2.0):** After each index rebuild, `cleanup_orphaned_sidecars()` deletes any `*.json` sidecar whose stem is not in the current chain-tip set. Skips files with names starting with `_` (index, daemon state). Applies across all profiles since all sidecars share one directory.

## Source Files

### `src/session_indexer_daemon.py`

The main daemon script. Key functions:

| Function | Purpose |
|---|---|
| `discover_profiles()` | Find all profile state.dbs |
| `compute_fingerprint()` | Cheap change detection: MD5(COUNT + MAX(started_at) + SUM(message_count)) |
| `read_chain_tips()` | SQL query for chain-tip sessions |
| `read_chain_messages()` | Walk parent chain, return full stitched message history |
| `make_sidecar()` | Build sidecar dict with real messages |
| `cleanup_orphaned_sidecars()` | Delete sidecars not in current chain-tip set |
| `process_profile()` | Per-profile sync with change detection |
| `poll_once()` | Full cycle: rebuild index + sidecars + cleanup |

### `src/ai.hermes.session-indexer.plist`

Launchd service definition. Replace `__YOUR_USERNAME__` with your macOS username before deploying.

| Key | Value |
|-----|-------|
| `RunAtLoad` | `true` — starts on login |
| `KeepAlive` | `true` — restarts if it crashes |
| `ThrottleInterval` | `10` — prevents rapid restart loops |
| `EnvironmentVariables` | Poll interval, WebUI URL, PATH |
