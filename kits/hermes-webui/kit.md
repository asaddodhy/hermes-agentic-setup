---
name: hermes-webui
description: "Fresh install and launchd daemonization of nesquena/hermes-webui with remote access via Tailscale Serve."
version: 2.0.0
author: dodhya
models:
  primary: any
services:
  tailscale:
    required: true
    description: "Tailscale userspace daemon for remote HTTPS access via Tailscale Serve"
    setup: "See tailscale-userspace kit — must be running with socket at ~/.hermes/tailscale.sock"
  groq:
    required: false
    description: "Groq API key for server-side STT (mic transcription)"
    setup: "Add GROQ_API_KEY to ~/hermes-webui/.env"
parameters:
  webui.host: 0.0.0.0
  webui.port: 8787
environment:
  os: [macos]
  hermes_version: ">=0.1.0"
dependencies:
  - tailscale-userspace
security:
  secrets_stored:
    - location: ~/hermes-webui/.env
      items: [HERMES_WEBUI_PASSWORD, GROQ_API_KEY]
  trust_boundaries:
    - Tailscale tailnet (encrypted mesh — only devices you authorize)
  known_threats:
    - Binding to 0.0.0.0 without password exposes WebUI to LAN
    - Tailscale Serve uses HTTPS only — HTTP clients cannot reach through it
tags: [hermes, webui, tailscale, remote-access, session-indexer]
next_steps:
  - kit: session-indexer-daemon
    reason: "Keeps the WebUI session list in sync with the desktop app — run immediately after this kit"
src:
  fileManifest:
    - path: src/configs/com.parantoux.hermes-webui.plist
      role: "launchd plist for WebUI daemon"
      destination: ~/Library/LaunchAgents/com.parantoux.hermes-webui.plist
---

# Hermes WebUI — Install & Remote Access Kit

## Goal

Install [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) and make it accessible both locally and remotely:

- **Local** — `http://localhost:8787` (desktop browser on this machine)
- **Remote** — `https://<your-tailscale-hostname>.ts.net` (any device on your tailnet)
- **launchd daemon** — survives sleep, auto-restarts on crash, starts on login

---

## When to Use

- Fresh machine setup — need the Hermes WebUI from nothing
- Restoring after a system wipe or new Mac
- After a failed WebUI update or corrupted install
- You have Tailscale running (or will set it up) and want remote browser access

---

## Setup

### Prerequisites

| Requirement | Check |
|-------------|-------|
| Hermes Agent installed and running | `hermes status` |
| Tailscale userspace daemon running | `tailscale --socket ~/.hermes/tailscale.sock status` |
| Homebrew installed | `brew --version` |
| Groq API key (for STT only) | Optional — skip if not needed |

### What this kit sets up

| Component | Location | Purpose |
|-----------|----------|---------|
| hermes-webui repo | `~/hermes-webui/` | WebUI source + bootstrap |
| WebUI launchd plist | `~/Library/LaunchAgents/com.parantoux.hermes-webui.plist` | Daemonize WebUI with auto-restart |
| `.env` | `~/hermes-webui/.env` | Password + optional Groq STT key |

### Dependencies from other kits

This kit references `tailscale-userspace` for the Tailscale daemon setup. If Tailscale isn't running yet, run that kit first.

---

## Steps

### Step 1 — Clone and bootstrap the WebUI

```bash
git clone https://github.com/nesquena/hermes-webui.git ~/hermes-webui
cd ~/hermes-webui
python3 bootstrap.py --no-browser
```

`bootstrap.py` detects the Hermes Agent venv, installs dependencies, and starts the server. Stop it with **Ctrl+C** — we'll use launchd for persistence.

### Step 2 — Configure `.env`

Write `~/hermes-webui/.env` using `write_file` (never use shell `echo >>` — it silently loses content in approval flows):

```dotenv
HERMES_WEBUI_PASSWORD=your-strong-password-here
GROQ_API_KEY=your-groq-api-key-here     # optional, for mic transcription
```

Verify:
```bash
grep -c "=" ~/hermes-webui/.env
# → 1 or 2 (1 if no Groq, 2 with Groq)
```

### Step 3 — Install launchd plist for WebUI

Copy the plist from the kit sources to `~/Library/LaunchAgents/`:

```bash
cp kits/hermes-webui/src/configs/com.parantoux.hermes-webui.plist \
   ~/Library/LaunchAgents/
```

**Key plist settings:**
| Setting | Value | Why |
|---------|-------|-----|
| `--host 0.0.0.0` | All interfaces | Required for Tailscale IP access |
| `KeepAlive` | `<true/>` | Auto-restart on crash |
| `RunAtLoad` | `<true/>` | Start on login |

Load and start:

```bash
# Unload if a previous version exists
launchctl bootout gui/$(id -u)/com.parantoux.hermes-webui 2>/dev/null; true

# Load the new plist
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.parantoux.hermes-webui.plist

# Verify
sleep 3
launchctl print gui/$(id -u)/com.parantoux.hermes-webui | grep -E 'state|pid'
```

Expected output: `state = running`, with a `pid` value.

### Step 4 — Enable Tailscale Serve for HTTPS

Tailscale Serve creates an HTTPS endpoint on port 443 that proxies to your local WebUI. This gives you a `https://<hostname>.ts.net` URL with automatic TLS certs — no manual cert management needed.

```bash
# Enable Tailscale Serve — proxies https://<hostname>.ts.net → http://localhost:8787
tailscale --socket="$HOME/.hermes/tailscale.sock" serve --bg \
  --https=443 / http://localhost:8787

# Verify
tailscale --socket="$HOME/.hermes/tailscale.sock" serve status
```

Expected output:
```
https://<your-hostname>.ts.net (tailnet only)
|-- / proxy http://localhost:8787
```

**Important:** If you already have a Tailscale Serve rule on port 8787 from an older setup, remove it — it intercepts HTTP traffic with a TLS handshake and breaks plain HTTP access:
```bash
tailscale --socket="$HOME/.hermes/tailscale.sock" serve --https=8787 off
```

### Step 5 — Verify the WebUI

```bash
# Local HTTP
curl -s http://localhost:8787/health

# Binding check — should show *:8787 (all interfaces)
lsof -i :8787 -P -n | grep LISTEN

# Check the log for any errors
tail -5 ~/.hermes/webui.log
```

Expected health response: `{"status": "ok", "sessions": 0, ...}`

### Step 6 — Test from another device

On any device logged into your Tailscale tailnet, open in a browser:

```
https://<your-tailscale-hostname>.ts.net
```

Where `<your-tailscale-hostname>` is the MagicDNS name shown by `tailscale status`. For example, if your machine shows as `mb16`, the URL is `https://mb16.tail1ed44d.ts.net`.

Log in with the `HERMES_WEBUI_PASSWORD` you set in Step 2.

### Step 7 — Set up the Session Indexer Daemon

The WebUI's session list will be empty after a fresh install — it has no way to discover the Hermes CLI sessions already in `~/.hermes/state.db`. The **session-indexer-daemon** bridges this gap: it polls all profiles every 15 seconds and keeps `_index.json` + sidecar files in sync with the desktop app.

Without this daemon:
- The WebUI sidebar shows no CLI sessions after a reinstall or sleep/wake
- Sessions that have been continued (compressed) keep appearing in the WebUI even after the desktop app has moved on to the chain tip
- Archived/deleted sessions can ghost back because stale sidecar files remain on disk

**Run the session-indexer-daemon kit immediately after completing this kit:**

```bash
# Deploy the daemon script
cp kits/session-indexer-daemon/src/session_indexer_daemon.py ~/.hermes/bin/
chmod +x ~/.hermes/bin/session_indexer_daemon.py

# Deploy and load the launchd plist (replace __YOUR_USERNAME__ with your macOS username)
sed "s/__YOUR_USERNAME__/$(whoami)/g" \
  kits/session-indexer-daemon/src/ai.hermes.session-indexer.plist \
  > ~/Library/LaunchAgents/ai.hermes.session-indexer.plist

launchctl load ~/Library/LaunchAgents/ai.hermes.session-indexer.plist

# Verify — should show a PID within 5 seconds
sleep 3 && launchctl list ai.hermes.session-indexer
tail -5 ~/.hermes/session-indexer.log
```

See the [session-indexer-daemon kit](../session-indexer-daemon/kit.md) for full details, configuration options, and troubleshooting.

---

## Constraints

- **Tailscale userspace mode** — the Mac itself cannot route to its own Tailscale IP. Testing `curl http://100.x.x.x:8787` from this machine will time out. Always test from another tailnet device.
- **Tailscale Serve only supports HTTPS** — it cannot proxy plain HTTP. Clients connecting via `http://<hostname>.ts.net` will see a TLS handshake error. Use `https://`.
- **HTTP still works via LAN IP** — if you need plain HTTP from another device on the same LAN, use `http://<lan-ip>:8787` (e.g. `http://192.168.1.193:8787`).
- **Password is required on `0.0.0.0`** — never bind to all interfaces without `HERMES_WEBUI_PASSWORD` set. Without it, any device on your network can access the WebUI without authentication.
- **launchd `bootout` + `bootstrap` required after plist changes** — `kickstart -k` ignores plist changes. Always do a full unload/reload when editing the plist.

---

## Safety Notes

- **WebUI password** — configure `HERMES_WEBUI_PASSWORD` before binding to `0.0.0.0`. This is your only auth barrier for remote access.
- **Tailscale state file** — `~/.hermes/tailscale-state.json` contains your Tailscale auth token. Back it up. If lost, you must re-authenticate.
- **Tailscale tailnet access** — only devices you authorize via the Tailscale admin console can reach your `*.ts.net` URLs. No public exposure.
- **Groq API key** — stored in plaintext in `.env`. Limit its scope in the Groq dashboard if concerned.
- **Logs contain no secrets** — `~/.hermes/webui.log` logs request paths and status codes but does not log headers, cookies, or request bodies.

---

## Failures Overcome

1. **`kickstart -k` ignores plist changes** — After editing the launchd plist, `launchctl kickstart -k` re-runs the process with launchd's cached arguments; it does NOT re-read the plist. Always use `bootout` then `bootstrap`.

2. **Tailscale Serve rule on port 8787 breaks HTTP** — A previous `tailscale serve --https=8787` rule intercepts all WireGuard traffic on port 8787 and presents a TLS handshake. HTTP clients get `HTTP 000`. Fix: `serve --https=8787 off`. Verify with `serve status`.

3. **`echo >>` silently destroys `.env`** — Using shell redirection (`echo "KEY=val" >> .env`) inside the agent's terminal approval flow can lose existing content or write nothing. Always use `write_file` with the COMPLETE file content.

4. **Tailscale IP unreachable from the Mac itself** — In userspace-networking mode there is no real `utun` interface. The Mac cannot route to `100.x.x.x`. All curl tests from this machine to the Tailscale IP will time out. This is expected — test from a phone or another tailnet device.

5. **Python venv path differs between systems** — The launchd plist hardcodes `/Users/dodhya/.hermes/hermes-agent/venv/bin/python`. On a fresh machine, bootstrap.py auto-detects or creates the venv. Update the plist path if the venv location differs.

---

## Verification

```
[ ] WebUI running: curl -s http://localhost:8787/health returns {"status": "ok"}
[ ] Binding all interfaces: lsof -i :8787 -P -n | grep "TCP \*:8787"
[ ] launchd managing WebUI: launchctl print gui/$(id -u)/com.parantoux.hermes-webui | grep "state = running"
[ ] Tailscale running: tailscale --socket ~/.hermes/tailscale.sock status shows your IP
[ ] Tailscale Serve active: tailscale --socket ~/.hermes/tailscale.sock serve status shows / → http://localhost:8787
[ ] .env has password: grep HERMES_WEBUI_PASSWORD ~/hermes-webui/.env
[ ] No Tailscale Serve rule on port 8787: tailscale --socket ~/.hermes/tailscale.sock serve status (must not show :8787)
[ ] Remote reachable from phone: https://<your-hostname>.ts.net loads login page
[ ] Mic works on phone: tap mic button, grants permission, transcribes
[ ] Session indexer daemon running: launchctl list ai.hermes.session-indexer (shows PID)
[ ] Session indexer polling: tail -3 ~/.hermes/session-indexer.log shows recent entries
[ ] WebUI session list populated: open WebUI sidebar — CLI sessions visible, chain tips only
```
