---
name: hermes-webui
description: "Full setup of the nesquena/hermes-webui frontend — local HTTP, remote HTTP over Tailscale, HTTPS via Caddy reverse proxy, Groq STT, and launchd daemonization on macOS."
version: 1.0.0
author: dodhya
models:
  primary: any
services:
  tailscale:
    required: true
    description: "Userspace Tailscale daemon for remote access via Tailscale IP"
    setup: "Must be running in userspace-networking mode with socket at ~/.hermes/tailscale.sock and state at ~/.hermes/tailscale-state.json"
  groq:
    required: false
    description: "Groq API for server-side STT (mic transcription)"
    setup: "Add GROQ_API_KEY to ~/hermes-webui/.env"
  caddy:
    required: false
    description: "Caddy reverse proxy for HTTPS on port 8443 (required for mobile mic)"
    setup: "brew install caddy; see Steps below"
parameters:
  webui.host: 0.0.0.0
  webui.port: 8787
  caddy.https_port: 8443
  tailscale.ip: 100.120.204.56
  tailscale.hostname: mb16.tail1ed44d.ts.net
environment:
  os: [macos]
  hermes_version: ">=0.1.0"
src:
  fileManifest:
    - path: src/configs/com.parantoux.hermes-webui.plist
      role: "launchd plist for WebUI daemon"
      destination: ~/Library/LaunchAgents/com.parantoux.hermes-webui.plist
    - path: src/configs/Caddyfile
      role: "Caddy reverse proxy config for HTTPS"
      destination: ~/.hermes/caddy/Caddyfile
    - path: src/configs/com.hermes.caddy.plist
      role: "launchd plist for Caddy daemon"
      destination: ~/Library/LaunchAgents/com.hermes.caddy.plist
---

# Hermes WebUI — Full Setup Kit

## Goal

Install and fully configure [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) — a rich web frontend for Hermes Agent — with:

- **Local HTTP** at `http://localhost:8787` (desktop browser)
- **Remote HTTP** at `http://100.120.204.56:8787` over Tailscale
- **Remote HTTPS** at `https://100.120.204.56:8443` via Caddy (required for mobile mic/STT)
- **Groq STT** for server-side speech transcription
- **launchd daemonization** for both WebUI and Caddy (survive sleep, auto-restart)

Both HTTP and HTTPS run simultaneously — same WebUI backend, two entry points.

---

## When to Use

- Fresh machine setup: need the Hermes WebUI installed from scratch
- Restoring after a system wipe or new Mac
- Adding HTTPS/mobile mic support to an existing HTTP-only WebUI setup
- After Tailscale is re-configured and remote access is broken

---

## Setup

### Prerequisites

| Requirement | Check |
|-------------|-------|
| Hermes Agent installed and running | `hermes status` |
| Tailscale userspace daemon running | `tailscale --socket ~/.hermes/tailscale.sock status` |
| Homebrew installed | `brew --version` |
| Groq API key (for STT only) | Optional — skip STT section if not needed |
| Self-signed TLS cert at `~/.hermes/tls/` | See Step 5 if missing |

### What this kit installs

| Component | Location | Purpose |
|-----------|----------|---------|
| hermes-webui repo | `~/hermes-webui/` | WebUI source + bootstrap |
| WebUI launchd plist | `~/Library/LaunchAgents/com.parantoux.hermes-webui.plist` | Daemonize WebUI |
| Caddy | `/opt/homebrew/bin/caddy` | HTTPS reverse proxy |
| Caddyfile | `~/.hermes/caddy/Caddyfile` | Caddy config |
| Caddy launchd plist | `~/Library/LaunchAgents/com.hermes.caddy.plist` | Daemonize Caddy |
| TLS cert | `~/.hermes/tls/hermes-webui-cert.pem` | Self-signed cert for HTTPS |
| TLS key | `~/.hermes/tls/hermes-webui-key.pem` | Private key for TLS cert |

---

## Steps

### Step 1 — Clone and bootstrap the WebUI

```bash
git clone https://github.com/nesquena/hermes-webui ~/hermes-webui
cd ~/hermes-webui
python3 bootstrap.py --no-browser
```

Bootstrap.py creates a venv, resolves the Hermes Agent path, and starts the server. Stop it with Ctrl+C — we'll use launchd instead.

### Step 2 — Configure .env

Write `~/hermes-webui/.env` using write_file (NEVER echo >> — see Failures Overcome #4):

```dotenv
HERMES_WEBUI_PASSWORD=your-strong-password-here
GROQ_API_KEY=your-groq-api-key-here
```

**Important:** Always use `write_file` with the COMPLETE file content. Never append with shell redirection — it silently loses content in approval flows.

Verify it was written:
```bash
grep -c "=" ~/hermes-webui/.env  # should return 2
```

### Step 3 — Configure Hermes STT (Groq)

```bash
hermes config set stt.enabled true
hermes config set stt.provider groq
```

The frontend's `_probeServerSttCapability()` auto-detects server STT and prefers it over the browser Web Speech API.

### Step 4 — Install launchd plist for WebUI

Copy `src/configs/com.parantoux.hermes-webui.plist` to `~/Library/LaunchAgents/`:

Key settings in the plist:
- `--host 0.0.0.0` — binds to all interfaces (required for Tailscale IP access)
- `KeepAlive` with `SuccessfulExit = false` — auto-restart on crash
- `StartOnMount` — re-launch after wake from sleep
- `ThrottleInterval 10` — prevents restart loops

```bash
cp kits/hermes-webui/src/configs/com.parantoux.hermes-webui.plist \
   ~/Library/LaunchAgents/

# Load and start
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.parantoux.hermes-webui.plist

# Verify
sleep 3
launchctl print gui/$(id -u)/com.parantoux.hermes-webui | grep -E 'state|pid'
curl -s http://localhost:8787/health | head -2
```

Expected: `state = running`, health returns `{"status": "ok", ...}`

### Step 5 — Generate self-signed TLS cert

```bash
mkdir -p ~/.hermes/tls

openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
  -keyout ~/.hermes/tls/hermes-webui-key.pem \
  -out ~/.hermes/tls/hermes-webui-cert.pem \
  -subj "/CN=HermesWebUI" \
  -addext "subjectAltName=IP:100.120.204.56"

chmod 600 ~/.hermes/tls/hermes-webui-key.pem
```

**Important:** The SAN must be `IP:100.120.204.56` (your Tailscale IP) — Chrome requires IP SANs for self-signed certs served by IP address. Replace with your actual Tailscale IP if different.

Verify:
```bash
openssl x509 -in ~/.hermes/tls/hermes-webui-cert.pem -noout -text \
  | grep -A1 "Subject Alternative"
# → IP Address:100.120.204.56
```

### Step 6 — Install Caddy

```bash
brew install caddy
caddy version  # confirm installed
```

### Step 7 — Write Caddyfile

Copy `src/configs/Caddyfile` to `~/.hermes/caddy/Caddyfile`, or write directly:

```
mkdir -p ~/.hermes/caddy
```

Content of `~/.hermes/caddy/Caddyfile`:
```
https://100.120.204.56:8443 {
    tls /Users/dodhya/.hermes/tls/hermes-webui-cert.pem /Users/dodhya/.hermes/tls/hermes-webui-key.pem
    reverse_proxy localhost:8787
}
```

**Critical:** Use explicit cert files (`tls <cert> <key>`), NOT `tls internal`. Caddy's internal CA fails on macOS with `tlsv1 alert internal error (SSL alert number 80)` due to LibreSSL incompatibility.

Validate:
```bash
caddy validate --config ~/.hermes/caddy/Caddyfile 2>&1 | grep -E "Valid|error"
# → Valid configuration
```

### Step 8 — Install launchd plist for Caddy

Copy `src/configs/com.hermes.caddy.plist` to `~/Library/LaunchAgents/`:

```bash
cp kits/hermes-webui/src/configs/com.hermes.caddy.plist \
   ~/Library/LaunchAgents/

# Load and start
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.hermes.caddy.plist

# Verify
sleep 3
launchctl print gui/$(id -u)/com.hermes.caddy | grep -E 'state|pid'
lsof -i :8443 -P -n | grep LISTEN
curl -sk https://localhost:8443/health | head -2
```

Expected: Caddy listening on `*:8443`, HTTPS health returns `{"status": "ok", ...}`

### Step 9 — Verify Tailscale daemon is running

```bash
tailscale --socket="$HOME/.hermes/tailscale.sock" status
# → Should show your devices and IP 100.120.204.56
```

If it shows "failed to connect" or "Logged out", restart it:
```bash
/opt/homebrew/opt/tailscale/bin/tailscaled \
  -tun=userspace-networking \
  -socket="$HOME/.hermes/tailscale.sock" \
  -state="$HOME/.hermes/tailscale-state.json" &
```

See `tailscale-userspace` kit for full daemon setup and persistence.

**Check for Tailscale Serve port conflicts** — critical for HTTP access:
```bash
tailscale --socket="$HOME/.hermes/tailscale.sock" serve status
```
If any rule appears on port 8787 (e.g. `https://...:8787 → proxy http://localhost:8787`), remove it:
```bash
tailscale --socket="$HOME/.hermes/tailscale.sock" serve --https=8787 off
```
Tailscale Serve **only supports HTTPS** — it cannot proxy plain HTTP. Any Serve rule on port 8787 intercepts all WireGuard traffic on that port and presents a TLS handshake, causing HTTP clients to fail with `HTTP 000`.

### Step 10 — Test all access points

```bash
# Local HTTP (desktop browser)
curl -s http://localhost:8787/health | head -2

# HTTPS via Caddy (mobile mic)
curl -sk https://localhost:8443/health | head -2

# Binding check
lsof -i :8787 -P -n | grep LISTEN  # should show *:8787
lsof -i :8443 -P -n | grep LISTEN  # should show *:8443
```

From your phone (Tailscale connected):
- `http://100.120.204.56:8787` — HTTP (no mic on Android Chrome)
- `https://100.120.204.56:8443` — HTTPS (mic works; accept self-signed cert warning once)
- `https://mb16.tail1ed44d.ts.net` — HTTPS via Tailscale Serve (mic works; automatic TLS cert, no browser warning)

---

## Constraints

- **Tailscale userspace mode** — the Mac itself cannot route to `100.120.204.56` locally (no real `utun` interface). Testing the Tailscale IP from the Mac via curl will always fail with exit 28. Only test from another device on the tailnet.
- **Self-signed cert browser warning** — Chrome shows "Your connection is not private" on first HTTPS visit. Tap Advanced → Proceed. This is expected and safe — traffic is already encrypted inside the Tailscale WireGuard tunnel.
- **Mic requires HTTPS** — Android Chrome blocks `getUserMedia()` on HTTP origins, even over Tailscale's encrypted tunnel. Must use `https://100.120.204.56:8443`.
- **Tailscale Serve in userspace mode** — `tailscale serve --https` may not work reliably in userspace-networking mode on macOS; the `*.ts.net` MagicDNS hostname doesn't register in the macOS system resolver. The Caddy approach avoids this entirely.
- **Admin password for firewall** — If macOS Application Firewall is enabled, the agent cannot modify it (requires `sudo`). In userspace-networking mode this is typically not required since tailscaled proxies connections locally, but if access fails this may be a factor.

---

## Safety Notes

- **Never bind WebUI to `0.0.0.0` without a password set in `.env`** — without `HERMES_WEBUI_PASSWORD`, any device on your network can access the WebUI without authentication.
- **Self-signed cert is for tailnet only** — the Caddy HTTPS endpoint is not publicly accessible (Tailscale IP only). Do not expose port 8443 to the public internet.
- **Tailscale state file** — `~/.hermes/tailscale-state.json` contains your Tailscale auth. Back it up (via backup-lite scanner). If lost, you must re-authenticate with `tailscale login`.
- **launchd plist changes** — after editing a plist's `ProgramArguments`, always do a full `bootout` + `bootstrap`. `kickstart -k` re-runs cached arguments and silently ignores plist changes.

---

## Failures Overcome

1. **`tailscale cert` fails in userspace mode** — `tailscale cert` requires `TailscaleVarRoot` which is not exposed in userspace-networking. Use self-signed cert + Caddy instead. Error: `500 Internal Server Error: no TailscaleVarRoot`.

2. **`tls internal` fails on macOS LibreSSL** — Caddy's built-in CA produces a cert that macOS LibreSSL rejects during the TLS handshake. Error: `tlsv1 alert internal error (SSL alert number 80)`. Fix: always provide explicit cert files with `tls <cert.pem> <key.pem>`.

3. **Binding `127.0.0.1` blocks all remote access** — The default launchd plist binds to `127.0.0.1`. Even with Tailscale running, the Tailscale IP `100.120.204.56` cannot reach a localhost-only socket. Fix: change plist `ProgramArguments` to `0.0.0.0`, then `bootout` + `bootstrap` (not `kickstart`).

4. **`echo >>` silently destroys `.env`** — Using shell redirection (`echo "KEY=val" >> .env`) inside the agent's terminal approval flow can lose existing content or write nothing. Always use `write_file` with the COMPLETE file content and verify afterwards with `grep` or `xxd`.

5. **`kickstart -k` ignores plist changes** — After changing `ProgramArguments` in the plist (e.g. host binding), `launchctl kickstart -k` re-runs the process with launchd's cached arguments — it does NOT re-read the plist. Must use `bootout` then `bootstrap`.

6. **Tailscale IP unreachable from Mac itself** — In userspace-networking mode, there is no real `utun` interface. The Mac cannot route to its own Tailscale IP (`100.120.204.56`). All `curl` tests from the Mac to this IP will time out with exit 28. This is expected — test from a phone or another tailnet device only.

7. **Tailscale daemon down = IP disappears** — `100.120.204.56` is a virtual Tailscale IP. If tailscaled stops (e.g. Mac sleep, crash), the IP ceases to exist and all remote connections fail immediately. Always check `tailscale status` before blaming the WebUI.

8. **`brew services start tailscale` runs without root** — The Homebrew launchd service for tailscaled fails silently because tailscaled requires root (or `--tun=userspace-networking`). It shows `Loaded: true, Running: false`. Fix: run tailscaled manually with `-tun=userspace-networking` flag instead.

9. **Wrong flags for tailscaled** — tailscaled uses single-dash flags (`-socket`, `-state`, `-tun`), not double-dash. Using `--socket` or `--state` causes it to print help and exit immediately.

10. **Tailscale Serve HTTPS rule intercepts HTTP on port 8787** — If a `--https=8787` Serve rule was set (e.g. from earlier testing), it captures all tailnet traffic on port 8787 and presents a TLS handshake. HTTP clients get `HTTP 000` (timeout/connect failure). Fix: `tailscale --socket ~/.hermes/tailscale.sock serve --https=8787 off`. Verify with `tailscale serve status` — the port 8787 entry must be absent before HTTP access works.

---

## Validation

```
[ ] WebUI running: curl -s http://localhost:8787/health returns {"status": "ok"}
[ ] WebUI binding all interfaces: lsof -i :8787 -P -n | grep "TCP \*:8787"
[ ] launchd managing WebUI: launchctl print gui/$(id -u)/com.parantoux.hermes-webui | grep "state = running"
[ ] Caddy running: lsof -i :8443 -P -n | grep LISTEN
[ ] HTTPS via Caddy: curl -sk https://localhost:8443/health returns {"status": "ok"}
[ ] launchd managing Caddy: launchctl print gui/$(id -u)/com.hermes.caddy | grep "state = running"
[ ] TLS cert has correct SAN: openssl x509 -in ~/.hermes/tls/hermes-webui-cert.pem -noout -text | grep "IP Address:100.120.204.56"
[ ] Tailscale running: tailscale --socket ~/.hermes/tailscale.sock status shows your IP
[ ] .env has password: grep HERMES_WEBUI_PASSWORD ~/hermes-webui/.env
[ ] .env has Groq key: grep GROQ_API_KEY ~/hermes-webui/.env
[ ] Remote HTTP reachable from phone: http://100.120.204.56:8787 loads login page
[ ] Remote HTTPS reachable from phone: https://100.120.204.56:8443 loads (after cert warning)
[ ] Mic works on phone: tap mic button in HTTPS WebUI, grant permission, speaks
[ ] Tailscale Serve has no rule on port 8787: tailscale --socket ~/.hermes/tailscale.sock serve status (must not show :8787)
[ ] WebUI sessions visible: all recent CLI/TUI sessions appear in WebUI sidebar (if not, run webui-session-discovery skill)
```
