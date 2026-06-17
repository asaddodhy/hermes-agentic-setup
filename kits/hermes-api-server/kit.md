---
name: hermes-api-server
description: "Deploy a remote Hermes Agent API server exposing an OpenAI-compatible HTTP API, enabling cross-machine agent orchestration via curl, Python SDK, or any OpenAI client."
version: 1.0.0
author: dodhya
models:
  primary: deepseek-v4-flash-free via opencode-zen
  required_models: []
services:
  hermes:
    required: true
    description: "Hermes Agent must be installed on the remote machine (mb14). The project lives at ~/.hermes/hermes-agent/ with a venv at venv/."
    setup: "Kit 1 (tailscale-userspace) + Kit 2 (ssh-key-auth) must be completed first, giving you SSH access to the remote."
parameters: {}
environment:
  os: [macos]
  homebrew: false
  hermes_version: ">=0.1.0"
src:
  fileManifest: []
  note: "This kit is entirely procedural — no source files to install. The API server is started via Hermes' built-in gateway command. Follow the steps in order."
---

## Goal

Expose the Hermes Agent runtime as an OpenAI-compatible HTTP API on a remote machine (mb14), reachable from the local machine (mb16) over LAN or Tailscale. This enables programmatic access to Hermes from any HTTP client — curl, Python SDK, Node.js, or any OpenAI-compatible chat/completions library.

The API server runs on **port 8642** and is authenticated via an API key stored in the remote's `~/.hermes/.env`.

## Architecture

```
┌─────────────────────────────────────┐       ┌──────────────────────────────────┐
│ Local (mb16)                        │       │ Remote (mb14)                    │
│                                     │       │                                  │
│  curl http://192.168.1.200:8642/*   │──────▶│  hermes gateway run              │
│  Python OpenAI SDK                  │  LAN  │  --accept-hooks                  │
│  Node.js OpenAI client              │  or   │  binds 127.0.0.1:8642            │
│                                     │ TSN   │  or 0.0.0.0:8642                 │
└─────────────────────────────────────┘       └──────────────────────────────────┘
```

The remote machine runs the Hermes gateway process in the background. The local machine sends HTTP requests to the remote's IP:8642. Tailscale (Kit 1) provides encrypted connectivity when off-LAN.

## When to Use

- **Programmatic agent access** — call Hermes from scripts, CI/CD pipelines, webhooks, or automation tools
- **Multi-machine orchestration** — local agent dispatches work to a remote Hermes instance
- **Integrating with external tools** — expose Hermes to Slack bots, Discord bots, n8n, Make, or custom frontends
- **Testing and development** — run Hermes behind a reverse proxy with TLS for safe internet exposure
- **After Kits 1 and 2 are complete** — this is kit #3 in the bootstrap sequence: (1) tailscale-userspace → (2) ssh-key-auth → (3) hermes-api-server + hermes-mcp-bridge → (4) security-hardening

## Setup

### What you need

| Item | Detail |
|------|--------|
| Local machine (control) | macOS, user `dodhya`, hostname `mb16` — this is where you run curl / SDK calls |
| Remote machine (node) | macOS, user `asadpreuss-dodhy`, hostname `mb14` (N719HT) — this runs the API server |
| LAN connection | Remote reachable at `192.168.1.200` (direct, best performance) |
| Optional — Tailscale | Remote reachable at `100.97.232.91` (encrypted, works across subnets) |
| SSH access | Passwordless SSH key auth from local→remote (Kit 2) or another working SSH path |
| Prerequisite kits | `tailscale-userspace` (Kit 1) + `ssh-key-auth` (Kit 2) |
| Remote Hermes | Hermes Agent installed at `~/.hermes/hermes-agent/` with venv at `venv/` |

### What this kit produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| API key | `~/.hermes/.env` (on mb14) | Random bearer token for API authentication |
| Gateway process | Running on mb14, port 8642 | Hermes gateway exposing OpenAI-compatible HTTP API |
| Local test result | Terminal output | Verification that the remote API is reachable and responding |

### Files this kit creates or modifies

| Path | Purpose |
|------|---------|
| `~/.hermes/.env` (on mb14) | Environment file containing `HERMES_API_KEY=<random>` — the API key used by the gateway |

## Steps

### Step 1: Verify prerequisites on the remote machine

SSH into the remote machine and confirm Hermes is installed and functional.

```bash
# From the local machine (mb16):
ssh mb14 "cd ~/.hermes/hermes-agent && source venv/bin/activate && hermes --version"
```

Expected output:
```
Hermes Agent version 0.x.x
```

Also verify the Hermes project structure:

```bash
ssh mb14 "ls ~/.hermes/hermes-agent/"
```

Expected output (subset):
```
venv/
...
```

If Hermes is not installed on the remote, install it first (see Hermes documentation for the remote machine). This kit assumes Hermes is already installed at `~/.hermes/hermes-agent/`.

---

### Step 2: Create or verify the API key

The Hermes API server authenticates requests via a bearer token stored in `~/.hermes/.env`. Generate a random key if one does not exist.

```bash
# Generate a random API key (64 hex chars / 256-bit strength)
RANDOM_KEY=$(openssl rand -hex 32)
echo "HERMES_API_KEY=$RANDOM_KEY" | ssh mb14 "cat > ~/.hermes/.env"
```

Verify the file was created correctly:

```bash
ssh mb14 "cat ~/.hermes/.env"
```

Expected output:
```
HERMES_API_KEY=7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b
```

> ⚠️ Treat this key like a password. Anyone with the key can call the Hermes API. The key is transmitted over SSH (encrypted by SSH itself) — it never appears in plaintext on the network.

> 🔁 **Already have an API key?** If `~/.hermes/.env` already exists on mb14, skip this step. Verify it with `ssh mb14 "cat ~/.hermes/.env"`.

---

### Step 3: Start the Hermes API server on the remote

The Hermes gateway is the API server process. Start it in the background on mb14, binding to the interface that the local machine can reach.

**Option A — Bind to all interfaces (LAN + Tailscale):**

This makes the API server reachable from any machine on the LAN or Tailscale tailnet.

```bash
ssh mb14 "cd ~/.hermes/hermes-agent && source venv/bin/activate && nohup python -m hermes gateway run --accept-hooks --host 0.0.0.0 --port 8642 > /tmp/hermes-gateway.log 2>&1 &"
```

> 🔁 **Alternative: bind only to localhost** for local-only access (no cross-machine). Use this when you only need the API server on the remote machine itself:
> ```bash
> ssh mb14 "cd ~/.hermes/hermes-agent && source venv/bin/activate && nohup python -m hermes gateway run --accept-hooks --host 127.0.0.1 --port 8642 > /tmp/hermes-gateway.log 2>&1 &"
> ```

**Option B — Bind to Tailscale IP specifically (optional):**

If you want to bind only to the Tailscale interface (not LAN), use the Tailscale IP:

```bash
ssh mb14 "cd ~/.hermes/hermes-agent && source venv/bin/activate && nohup python -m hermes gateway run --accept-hooks --host 100.97.232.91 --port 8642 > /tmp/hermes-gateway.log 2>&1 &"
```

**Option C — Hermes background terminal approach:**

If you prefer to manage the process through Hermes' process tracking (useful for long-lived servers):

```bash
# On the remote machine, inside a Hermes session or terminal:
cd ~/.hermes/hermes-agent && source venv/bin/activate && python -m hermes gateway run --accept-hooks
```

> ⚠️ **About `--accept-hooks`:** This flag tells the gateway to automatically approve shell operations dispatched via the API. Without it, every operation that triggers a shell command will be blocked waiting for manual approval — which defeats the purpose of an API server. Understand the security implications: any caller with the API key can execute arbitrary shell commands on the remote machine.

---

### Step 4: Verify the gateway process is running

Confirm the process started successfully and is listening on port 8642.

```bash
# Check process is running
ssh mb14 "ps aux | grep 'hermes gateway' | grep -v grep"
```

Expected output:
```
asadpreu+ 12345   0.1  0.2  ... python -m hermes gateway run --accept-hooks --host 0.0.0.0 --port 8642
```

Check that the port is listening:

```bash
ssh mb14 "lsof -i :8642 | grep LISTEN"
```

Expected output:
```
Python    12345  asadpreuss-dodhy    ...  TCP *:8642 (LISTEN)
```

Check the log file for startup messages:

```bash
ssh mb14 "tail -5 /tmp/hermes-gateway.log"
```

Expected output (approximate):
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8642
```

---

### Step 5: Test the API endpoint from the local machine

From the local machine (mb16), send a health check request to the remote API server.

**Via LAN (direct):**

```bash
curl -s http://192.168.1.200:8642/health | python3 -m json.tool
```

**Via Tailscale (encrypted, off-LAN):**

```bash
curl -s http://100.97.232.91:8642/health | python3 -m json.tool
```

Expected output:
```json
{
  "status": "ok",
  "version": "0.x.x"
}
```

> 🔁 If the health endpoint returns a different shape, that's fine — the important thing is that you get a JSON response and HTTP 200. If you get `Connection refused` or timeout, see the troubleshoot section.

---

### Step 6: Test a chat completion request

Now test the OpenAI-compatible chat completions endpoint. This exercises the full request path including authentication.

```bash
# Fetch the API key from the remote to use locally
API_KEY=$(ssh mb14 "cat ~/.hermes/.env | grep HERMES_API_KEY | cut -d= -f2")

# Send a chat completion request
curl -s http://192.168.1.200:8642/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "user", "content": "Say hello in exactly one sentence."}
    ],
    "max_tokens": 100
  }' | python3 -m json.tool
```

Expected output (trimmed):
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1718000000,
  "model": "default",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm Hermes Agent, your AI assistant."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 12,
    "total_tokens": 30
  }
}
```

If you get `{"detail":"Unauthorized"}` or HTTP 403, the API key in the `Authorization` header doesn't match the key in `~/.hermes/.env` on the remote. Verify both are the same.

---

### Step 7: Test with the Python OpenAI SDK (optional)

If you use Python on the local machine, validate the SDK integration:

```bash
# Install the OpenAI Python library
pip install openai

# Run a quick test
python3 << 'EOF'
from openai import OpenAI
import subprocess
import re

# Fetch the remote API key
result = subprocess.run(
    ["ssh", "mb14", "cat ~/.hermes/.env | grep HERMES_API_KEY | cut -d= -f2"],
    capture_output=True, text=True
)
api_key = result.stdout.strip()

client = OpenAI(
    base_url="http://192.168.1.200:8642/v1",
    api_key=api_key,
)

response = client.chat.completions.create(
    model="default",
    messages=[{"role": "user", "content": "Say hello in exactly one sentence."}],
    max_tokens=100,
)

print(f"Response: {response.choices[0].message.content}")
print(f"Tokens used: {response.usage.total_tokens}")
EOF
```

Expected output:
```
Response: Hello! I'm Hermes Agent, your AI assistant.
Tokens used: 30
```

---

### Step 8: Set up automatic restart (recommended)

The gateway process started via SSH will terminate when the SSH session ends (depending on how `nohup` works in the remote environment). For a production setup, configure the process to survive terminal closures and machine reboots.

**Option A — Launchd plist (macOS, recommended):**

Create a launchd plist on the remote machine to auto-start the gateway on login:

```bash
# Transfer and install the launchd plist (we'll create it below)
cat > /tmp/com.hermes.gateway.plist << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/python</string>
        <string>-m</string>
        <string>hermes</string>
        <string>gateway</string>
        <string>run</string>
        <string>--accept-hooks</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8642</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/asadpreuss-dodhy/.hermes/hermes-agent</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/hermes-gateway.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/hermes-gateway.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string>
        <key>HERMES_HOME</key>
        <string>/Users/asadpreuss-dodhy/.hermes</string>
    </dict>
</dict>
</plist>
PLIST

# Copy to remote and load
scp /tmp/com.hermes.gateway.plist mb14:/tmp/
ssh mb14 "mv /tmp/com.hermes.gateway.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.hermes.gateway.plist"
```

Verify it loaded:

```bash
ssh mb14 "launchctl list | grep com.hermes.gateway"
```

Expected output:
```
PID    ...  com.hermes.gateway
```

**Option B — tmux session:**

If launchd is not available or you prefer manual control, use tmux:

```bash
ssh mb14 "tmux new-session -d -s hermes-gateway 'cd ~/.hermes/hermes-agent && source venv/bin/activate && python -m hermes gateway run --accept-hooks --host 0.0.0.0 --port 8642'"
```

Reattach with `ssh mb14 "tmux attach -t hermes-gateway"`.

---

### Step 9: Security hardening — restrict API key access

The API key in `~/.hermes/.env` grants full access to the Hermes gateway, including arbitrary shell execution via `--accept-hooks`. Protect it.

On the remote machine:

```bash
ssh mb14 "chmod 600 ~/.hermes/.env && chmod 700 ~/.hermes"
```

Verify:

```bash
ssh mb14 "ls -la ~/.hermes/.env"
```

Expected output:
```
-rw-------  1 asadpreuss-dodhy  staff  53 Jun 17 12:00 /Users/asadpreuss-dodhy/.hermes/.env
```

---

## Constraints

- **The gateway process started via `nohup` or SSH may terminate** when the SSH session ends if not properly daemonized. Use the launchd plist (Step 8, Option A) or tmux (Option B) for persistence.
- **`--accept-hooks` is required** for the API server to execute shell commands. Without it, every operation requiring shell access will be blocked waiting for manual approval, making the API server effectively unusable for automation.
- **The API key is transmitted as a bearer token** in HTTP headers. On an untrusted network (e.g., public Wi-Fi), an attacker could intercept the token. Always use LAN or Tailscale; never expose the API server to the public internet without TLS.
- **Tailscale performance** is slightly lower than direct LAN due to WireGuard encryption overhead. Use the LAN IP (`192.168.1.200`) for latency-sensitive operations and the Tailscale IP (`100.97.232.91`) for off-subnet access.
- **The gateway binds to the specified interface** — `0.0.0.0` binds to all interfaces (LAN + Tailscale + localhost). `127.0.0.1` binds only to localhost (no cross-machine access). A specific Tailscale IP binds only to that interface.
- **Only one gateway process per port** — if you start a second gateway on the same port, the first one will be terminated or the second will fail with `Address already in use`. Kill the existing process first if needed.
- **Profile isolation:** The API key in `~/.hermes/.env` is profile-agnostic — it applies to whichever Hermes profile the gateway process runs under. The `team-manager` profile's `.env` would be at `~/.hermes/profiles/team-manager/.env` if profile-scoped.

## Safety Notes

- **`--accept-hooks` is powerful and dangerous.** It auto-approves any shell operation dispatched through the API. A caller with the API key can execute arbitrary commands on the remote machine. Only use on trusted networks.
- **Never expose the gateway (port 8642) to the public internet** without a reverse proxy and TLS. If you need internet access, add a reverse proxy (Caddy, Nginx + Let's Encrypt) that terminates TLS and optionally adds rate-limiting.
- **The API key file (`~/.hermes/.env`) must be readable only by the remote user.** Step 9 sets `chmod 600`. If another user on the remote machine can read this file, they can call the API.
- **Rotate the API key periodically.** If you suspect the key was compromised, generate a new one (Step 2) and restart the gateway (kill the old process, start a new one).
- **The gateway logs (`/tmp/hermes-gateway.log`) may contain request data and responses.** Protect this log file from other users on the remote machine: `chmod 600 /tmp/hermes-gateway.log`.
- **Consider restricting what the API user can do** by running the gateway under a dedicated macOS user account with limited permissions, especially on production machines.
- **Do NOT use `--accept-hooks` if you intend to gate shell operations through approval prompts** — the flag exists specifically to bypass approvals for automation. If you need per-operation approval, omit the flag and design your workflow around manual approval prompts.

## Failures Overcome

1. **Process dies after SSH session ends** — `nohup` + `&` does not guarantee persistence on all macOS configurations if the SSH client sends SIGHUP. Use the launchd plist (Step 8) for reliable auto-restart on login and crash recovery.

2. **`Address already in use` when starting the gateway** — A previous gateway process is still running on port 8642. Kill it with:
   ```bash
   ssh mb14 "lsof -ti :8642 | xargs kill -9"
   ```

3. **API returns `{"detail":"Unauthorized"}`** — The API key in the `Authorization` header does not match `HERMES_API_KEY` in `~/.hermes/.env` on the remote. Common causes: (a) the key was regenerated after the gateway started (restart the gateway), (b) SSH fetched the key from a different path, (c) the `.env` file has trailing whitespace. Verify with `ssh mb14 "cat ~/.hermes/.env | xxd | head -3"`.

4. **`Connection refused` on LAN IP** — Possible causes: (a) gateway not running (check with `ps aux | grep gateway`), (b) gateway bound to `127.0.0.1` instead of `0.0.0.0`, (c) macOS firewall blocking the port (System Settings → Network → Firewall → allow `Python` or adjust), (d) wrong LAN IP or port. Verify with `ssh mb14 "lsof -i :8642"` to see the binding address.

5. **`Connection refused` on Tailscale IP** — Possible causes: (a) Tailscale daemon not running on remote, (b) wrong tailscale IP (verify with `ssh mb14 "tailscale --socket ~/.hermes/tailscale.sock ip -1"`), (c) gateway not bound to `0.0.0.0` (only `127.0.0.1`, so Tailscale traffic from another IP is dropped). Fix by binding to `0.0.0.0`.

6. **Gateway starts but hangs or crashes immediately** — The Hermes gateway may fail silently if the environment is misconfigured. Check `/tmp/hermes-gateway.log` for errors. Common issues: (a) missing model configuration, (b) Hermes version mismatch, (c) Python dependency not installed in the venv.

7. **`hermes gateway run` not found** — The Hermes CLI may not include the gateway command in the installed version, or the venv is not activated. Verify: `ssh mb14 "cd ~/.hermes/hermes-agent && source venv/bin/activate && hermes --help | grep gateway"`. If `gateway` is not listed, upgrade Hermes or install the gateway plugin.

8. **Multi-key authentication confusion** — If the SSH agent on the local machine has many keys loaded, the remote machine may disconnect before the correct key is tried. The SSH config alias (`mb14`) in Kit 2 mitigates this with the `IdentityFile` directive. If you're not using the alias, add `-i ~/.ssh/id_ed25519` to the SSH command.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` | Gateway not running or wrong interface | `ssh mb14 "lsof -i :8642"` to check; restart with correct `--host` |
| `Unauthorized` | API key mismatch | Verify `cat ~/.hermes/.env` matches the `Authorization` header value |
| `502 Bad Gateway` | Hermes backend error | Check `/tmp/hermes-gateway.log` for Python tracebacks |
| `Connection reset` | Process crashed | Restart the gateway and investigate logs |
| `Address already in use` | Old process lingering | `ssh mb14 "lsof -ti :8642 \| xargs kill -9"` |
| Can't SSH (key fail) | SSH config or key issue | Verify `ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes asadpreuss-dodhy@192.168.1.200` |
| `command not found: hermes` | Venv not activated | Use full path: `~/.hermes/hermes-agent/venv/bin/hermes` |

## Validation

After completing all steps, this checklist confirms the Hermes API server is fully operational:

- [ ] Remote Hermes installed: `ssh mb14 "cd ~/.hermes/hermes-agent && source venv/bin/activate && hermes --version"` → shows version
- [ ] API key file exists: `ssh mb14 "cat ~/.hermes/.env"` → shows `HERMES_API_KEY=<hex>`
- [ ] API key file permissions: `ssh mb14 "stat -f '%A' ~/.hermes/.env"` → `600` (or `-rw-------`)
- [ ] Gateway process running: `ssh mb14 "ps aux | grep 'hermes gateway' | grep -v grep"` → process with `--accept-hooks`
- [ ] Port listening: `ssh mb14 "lsof -i :8642 | grep LISTEN"` → `TCP *:8642 (LISTEN)`
- [ ] Health check (LAN): `curl -s http://192.168.1.200:8642/health` → returns JSON with `status: ok`
- [ ] Health check (Tailscale): `curl -s http://100.97.232.91:8642/health` → returns JSON with `status: ok`
- [ ] Chat completion (authenticated): `curl -s http://192.168.1.200:8642/v1/chat/completions -H "Authorization: Bearer <api-key>" -d '{"model":"default","messages":[{"role":"user","content":"hi"}]}'` → returns JSON with `choices[0].message.content`
- [ ] Python SDK works: `python3 -c "from openai import OpenAI; ..."` → returns response (if SDK installed)
- [ ] Auto-restart configured: `ssh mb14 "launchctl list | grep com.hermes.gateway"` → shows PID (if using launchd)
- [ ] Log file exists: `ssh mb14 "tail -3 /tmp/hermes-gateway.log"` → shows startup info
- [ ] Unauthorized request blocked: `curl -s -o /dev/null -w '%{http_code}' http://192.168.1.200:8642/v1/chat/completions -H "Authorization: Bearer invalid-key"` → returns `403` or `401`
