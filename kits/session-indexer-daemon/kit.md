---
name: session-indexer-daemon
description: "Bridges Hermes CLI/TUI sessions from state.db into the WebUI session index — polls every 15s, writes only chain-tip sessions, rebuilds the index from scratch each cycle."
version: 1.0.0
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
tags: [sessions, webui, daemon, sync, chain-tip]
src:
  fileManifest:
    - src/session_indexer_daemon.py
    - src/ai.hermes.session-indexer.plist
---

# Session Indexer Daemon

## Goal

Keep the Hermes WebUI session index (`_index.json`) in sync with the CLI/desktop app's sessions — showing only **chain-tip sessions** (the latest session in each continuation chain), rebuilt from scratch every poll cycle so stale entries never accumulate.

## When to Use

- After installing the Hermes WebUI and you want the session list to match the desktop app
- Sessions that have been continued (compressed) keep showing up in the WebUI
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
                                          │  writes to           │
                                          │  _index.json         │
                                          │  + sidecar .json     │
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

The daemon:

1. **Discovers all Hermes profiles** by scanning `~/.hermes/state.db` (default) and `~/.hermes/profiles/*/state.db` (named profiles)
2. **Queries chain tips** — sessions not referenced as a parent by any other TUI/CLI/WebUI/Telegram session (subagent sub-sessions are correctly excluded — they are NOT continuations)
3. **Rebuilds `_index.json` from scratch** each cycle — no stale accumulation
4. **Writes missing sidecar `.json` files** for each session
5. **Nudges the WebUI** to warm its session cache

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

### Step 3 — Verify the daemon is running

```bash
# Check process
launchctl list ai.hermes.session-indexer

# Check log
tail -5 ~/.hermes/session-indexer.log
```

Expected output shows polls every ~15 seconds:

```
2026-06-20 00:30:19 [INFO] Rebuilt _index.json with 21 entries from 3 profile(s)
2026-06-20 00:30:19 [INFO] Poll #1: +21 index entries, +0 sidecars
```

### Step 4 — Check the WebUI session list

Open the WebUI in your browser and verify the session list in the sidebar shows the correct chain-tip sessions — only the latest session in each continuation chain.

### Restarting after updates

If you update the daemon script:

```bash
launchctl kickstart -k gui/$(id -u)/ai.hermes.session-indexer
```

This kills any existing instance and starts a new one with the updated code.

## Configuration

The daemon respects these environment variables (set in the plist's `EnvironmentVariables` dict):

| Variable | Default | Description |
|----------|---------|-------------|
| `DAEMON_POLL_INTERVAL` | `15` | Seconds between poll cycles |
| `HERMES_WEBUI_URL` | `http://127.0.0.1:8787` | WebUI HTTP server URL |

## Constraints

- **macOS only** — relies on launchd for lifecycle management. On Linux, a systemd user service would be needed
- **Python 3.11+** — uses `pathlib.Path` extensively. The Hermes venv provides this
- **WebUI must be running** — the daemon writes to the same sessions directory the WebUI reads from. If the WebUI is stopped, the index still gets written but the WebUI won't pick it up until next start
- **No cross-platform** — not designed for Windows. The launchd plist is macOS-specific
- **Sidecar cleanup not automatic** — orphaned sidecar `.json` files (from sessions that are no longer chain tips) are not cleaned up by the daemon. Run `session-indexer-daemon/scripts/clean-orphaned-sidecars.sh` if needed

### Troubleshooting orphaned sidecars

If `~/.hermes/webui/sessions/` accumulates `.json` files for sessions no longer in the index, run:

```bash
python3 -c "
import json, pathlib
idx_path = pathlib.Path.home() / '.hermes/webui/sessions/_index.json'
if not idx_path.exists(): exit(0)
idx = json.loads(idx_path.read_text())
valid_ids = {i['session_id'] for i in idx if i.get('session_id')}
for f in pathlib.Path.home().glob('.hermes/webui/sessions/*.json'):
    if f.name in ('_index.json','_index.json.tmp','_daemon_state.json'): continue
    if f.stem not in valid_ids:
        print(f'Removing {f.name}')
        f.unlink()
"
```

## Chain-Tip Logic

The daemon's core SQL determines which sessions are chain tips:

```sql
-- A session is a chain tip if:
SELECT id, title, source, message_count
FROM sessions
WHERE message_count > 0
  AND title IS NOT NULL
  AND (source IN ('tui', 'cli') OR source IS NULL)          -- only CLI/TUI sessions are displayed
  AND (archived IS NULL OR archived = 0)                    -- not archived
  AND id NOT IN (
      SELECT DISTINCT parent_session_id FROM sessions
      WHERE parent_session_id IS NOT NULL
        AND source IN ('tui', 'cli', 'webui', 'telegram')   -- any child of these types = continuation
  )
```

Key design decisions:

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Sources displayed** | `tui`, `cli`, `NULL` | WebUI and Telegram sessions exist in state.db but are bridge entries — the daemon only surfaces desktop CLI sessions |
| **Continuation types** | `tui`, `cli`, `webui`, `telegram` | If a session has a child from any of these sources, it's been "continued" and is no longer the chain tip |
| **Subagent exclusion** | `subagent` NOT in continuation list | Subagent sub-sessions are internal task spawns, NOT user continuations. They don't affect chain-tip status |
| **Index rebuild** | From scratch every cycle | Ensures superseded chain tips are automatically removed — no stale accumulation |

## Verification Checklist

- [ ] Daemon script deployed: `ls -la ~/.hermes/bin/session_indexer_daemon.py`
- [ ] Launchd plist deployed: `ls -la ~/Library/LaunchAgents/ai.hermes.session-indexer.plist`
- [ ] Daemon running: `launchctl list ai.hermes.session-indexer` shows a PID
- [ ] Daemon polling: `tail -3 ~/.hermes/session-indexer.log` shows recent poll entries
- [ ] Index populated: `ls -la ~/.hermes/webui/sessions/_index.json` exists and has entries
- [ ] WebUI shows correct sessions: Open WebUI sidebar — only chain tips visible

## Failures Overcome

### Bug 1: Source filter too narrow (v1)

The original child-exclusion subquery only checked for `tui`/`cli` children:

```sql
AND (source IN ('tui', 'cli') OR source IS NULL)
```

This meant a TUI parent with WebUI-only children was incorrectly treated as a chain tip. The root session of the "Hermes WebUI Reinstallation" chain kept being recovered.

**Fix:** Added `'webui'` and `'telegram'` to the continuation source list. Removed the `OR source IS NULL` catch-all (no actual NULL-source children existed):

```sql
AND source IN ('tui', 'cli', 'webui', 'telegram')
```

### Bug 2: Append-only index (v1)

The daemon only **appended** new chain tips to `_index.json` — it never removed superseded entries. After multiple continuations in the same chain, the index had 6 entries for the same chain (root, #2, #4, #5, #6, #8) when it should have had only 1 (#8).

**Fix:** Changed `poll_once()` to rebuild `_index.json` from scratch each cycle using only current chain tips. No append, no stale accumulation.

## Source Files

### `src/session_indexer_daemon.py`

The main daemon script (~485 lines). Handles:
- Profile discovery (default + named profiles)
- Fingerprint-based change detection (MD5 of row count + MAX started_at)
- Chain-tip SQL queries against each profile's state.db
- Sidecar file creation/management
- Atomic index writes (tmp + os.replace)
- Graceful shutdown on SIGTERM/SIGINT

### `src/ai.hermes.session-indexer.plist`

Launchd service definition. Replace `__YOUR_USERNAME__` with your macOS username before deploying. Key settings:

| Key | Value |
|-----|-------|
| `RunAtLoad` | `true` — starts on login |
| `KeepAlive` | `true` — restarts if it crashes |
| `ThrottleInterval` | `10` — prevents rapid restart loops |
| `EnvironmentVariables` | Poll interval, WebUI URL, PATH |
