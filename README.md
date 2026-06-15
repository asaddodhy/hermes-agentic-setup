# Hermes Multi-Machine Setup

> **Created:** June 15, 2026
> **Author:** Hermes Agent (mb16 — this machine)
> **Machines:**
> - **mb16** — MacBook, user `dodhya`, Tailscale IP `100.120.204.56`
> - **mb14** — MacBook (N719HT), user `asadpreuss-dodhy`, Tailscale IP `100.97.232.91`, LAN IP `192.168.1.200`
> - Also on tailnet: `pixel-10-pro-xl` (Android, offline)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Profile Setup: team-manager](#2-profile-setup-team-manager)
3. [Tailscale Installation & Configuration](#3-tailscale-installation--configuration)
4. [SSH Key-Based Authentication](#4-ssh-key-based-authentication)
5. [MCP Server Connection (Messaging Tools)](#5-mcp-server-connection-messaging-tools)
6. [API Server Connection (Full Agent)](#6-api-server-connection-full-agent)
7. [Usage Guide](#7-usage-guide)
8. [Troubleshooting](#8-troubleshooting)
9. [Security Notes](#9-security-notes)

---

## 1. Architecture Overview

```
┌─────────────────┐          ┌─────────────────┐
│  mb16 (THIS)    │          │  mb14 (REMOTE)  │
│                 │          │                  │
│  Hermes Agent   │◄────────►│  Hermes Agent    │
│  (Chat UI)      │  Tailnet │  (API Server)    │
│                 │  (VPN)   │  :8642           │
│  MCP Client ────┤          │  ┌─────────────┐ │
│  (mb14 server)  │          │  │ MCP Server  │ │
│                 │          │  │ (SSH stdio) │ │
└─────────────────┘          └─────────────────┘
```

**Two connection methods are available:**

1. **MCP Server** (section 5) — exposes mb14's messaging gateway tools as MCP tools in this Hermes session. Runs over SSH stdio transport.
2. **API Server** (section 6) — exposes mb14's full agent capabilities via an OpenAI-compatible HTTP API. Allows two-way agent-to-agent communication.

---

## 2. Profile Setup: team-manager

This setup was performed from the **team-manager** profile on mb16. Profiles provide isolated configurations, skills, sessions, and memory.

### Checking active profile

```bash
hermes profile list
hermes profile show
```

The current profile is shown at session start. Profile configs live under `~/.hermes/profiles/<name>/`.

### Default profile vs named profiles

- `~/.hermes/config.yaml` — default profile configuration
- `~/.hermes/profiles/<name>/config.yaml` — named profile configuration

MCP servers and other profile-specific settings are stored per-profile. To make an MCP server available in another profile, you must add it there as well.

---

## 3. Tailscale Installation & Configuration

Tailscale creates a secure mesh VPN between machines using WireGuard. Both machines join the same tailnet and can communicate over private `100.x.x.x` IPs that are encrypted end-to-end.

### Install on macOS (Homebrew)

```bash
brew install tailscale
```

### Start in userspace mode (no root/sudo needed)

Standard Tailscale requires root for the kernel-level TUN device. Userspace networking avoids this:

```bash
# Start the daemon
/opt/homebrew/opt/tailscale/bin/tailscaled \
  --tun=userspace-networking \
  --state=/Users/<user>/.hermes/tailscale-state.json \
  --socket=/Users/<user>/.hermes/tailscale.sock \
  > /tmp/tailscaled.log 2>&1 &

# Authenticate
tailscale --socket /Users/<user>/.hermes/tailscale.sock up
# Opens a URL in the browser. Log in with your Tailscale account.
```

**Important:** Tilde expansion (`~`) does NOT work in `tailscaled` arguments because the `=` sign in `--state=~/.hermes/...` prevents the shell from expanding it. Use full absolute paths.

### Verify connection

```bash
tailscale --socket /Users/<user>/.hermes/tailscale.sock status
```

Expected output:
```
100.x.x.x  hostname  user@  OS    -
```

A `-` status means directly connected. `offline` means the device is registered but currently unreachable.

### Userspace mode flags explained

| Flag | Purpose |
|------|---------|
| `--tun=userspace-networking` | Uses userland networking instead of kernel TUN driver (no root) |
| `--state=<path>` | Persistent state file (auth tokens, node key) |
| `--socket=<path>` | Unix socket for CLI communication (default `/var/run/tailscaled.socket` requires root) |

### Managing the daemon

```bash
# Kill the daemon
pkill tailscaled

# Restart
pkill tailscaled && /opt/homebrew/opt/tailscale/bin/tailscaled \
  --tun=userspace-networking \
  --state=/Users/<user>/.hermes/tailscale-state.json \
  --socket=/Users/<user>/.hermes/tailscale.sock \
  > /tmp/tailscaled.log 2>&1 &
```

---

## 4. SSH Key-Based Authentication

Passwordless SSH from mb16 → mb14 enables automated MCP and API calls without interactive prompts.

### Prerequisites (on mb14)

- **macOS Remote Login** must be enabled: System Settings → General → Sharing → Remote Login
- Username: `asadpreuss-dodhy`
- LAN IP: `192.168.1.200`
- Tailscale IP: `100.97.232.91`

### Generate SSH key (on mb16)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
```

### Copy public key to mb14

```bash
ssh-copy-id asadpreuss-dodhy@192.168.1.200
# Or manually:
cat ~/.ssh/id_ed25519.pub | ssh asadpreuss-dodhy@192.168.1.200 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Test passwordless connection

```bash
ssh asadpreuss-dodhy@192.168.1.200 "hostname; whoami"
```

The connection should work without a password prompt.

### Connection paths

| Path | When to use |
|------|-------------|
| `asadpreuss-dodhy@192.168.1.200` | LAN (best performance, same network) |
| `asadpreuss-dodhy@100.97.232.91` | Tailscale (encrypted end-to-end, works across networks) |

---

## 5. MCP Server Connection (Messaging Tools)

The Hermes MCP server exposes the remote agent's messaging gateway tools (read/send messages, list conversations, etc.). The server runs over stdio, which is tunneled through SSH.

### On mb14 (remote)

The MCP server command is:
```bash
/Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes mcp serve --accept-hooks
```

The `hermes` CLI wrapper at `~/.local/bin/hermes` does NOT pass through properly over SSH (it's a bash script that sets up the environment and execs the venv binary). Use the venv path directly for reliability.

### On mb16 (this machine)

Add as an MCP client:
```bash
hermes mcp add mb14 \
  --command ssh \
  --args asadpreuss-dodhy@192.168.1.200 \
    /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes \
    mcp serve --accept-hooks
```

This adds an entry to the current profile's `config.yaml`:
```yaml
mcp_servers:
  mb14:
    command: ssh
    args:
      - asadpreuss-dodhy@192.168.1.200
      - /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes
      - mcp
      - serve
      - --accept-hooks
```

### What it exposes

The MCP server registers 10 tools for mb14's messaging gateway:

| Tool | Purpose |
|------|---------|
| `mcp_mb14_conversations_list` | List active conversations on mb14's platforms |
| `mcp_mb14_conversation_get` | Get conversation details |
| `mcp_mb14_messages_read` | Read recent messages from a conversation |
| `mcp_mb14_messages_send` | Send a message via mb14's connected platforms |
| `mcp_mb14_attachments_fetch` | List attachments for a message |
| `mcp_mb14_events_poll` | Poll for new events |
| `mcp_mb14_events_wait` | Long-poll for the next event |
| `mcp_mb14_channels_list` | List available channels/targets |
| `mcp_mb14_permissions_list_open` | List pending approval requests |
| `mcp_mb14_permissions_respond` | Respond to approval requests |

### Refresh on config change

```bash
/reload-mcp   # within Hermes session
# Or restart the session: /reset
```

### Make available in other profiles

```bash
hermes profile use <other-profile>
hermes mcp add mb14 --command ssh --args asadpreuss-dodhy@192.168.1.200 \
  /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes \
  mcp serve --accept-hooks
```

---

## 6. API Server Connection (Full Agent)

The API Server exposes mb14's Hermes as a full agent via an OpenAI-compatible HTTP API. This is the primary method for agent-to-agent communication — send a prompt, get back a response after the remote agent runs its full tool loop.

### Enable API Server on mb14

Add to `~/.hermes/.env` on mb14:
```bash
API_SERVER_ENABLED=true
API_SERVER_KEY=<generate-a-random-key>
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8642
```

Or directly in `~/.hermes/config.yaml` (under gateway platforms).

### Start the gateway on mb14

```bash
hermes gateway run --accept-hooks
```

This starts the gateway process, which loads all enabled platform adapters including the API Server.

### Verify the server

```bash
# Health check (no auth required)
curl http://192.168.1.200:8642/health

# List models (auth required)
curl -H "Authorization: Bearer <API_KEY>" http://192.168.1.200:8642/v1/models

# Chat completion
curl -X POST http://192.168.1.200:8642/v1/chat/completions \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hermes-agent",
    "messages": [{"role": "user", "content": "What is the time and uptime?"}],
    "max_tokens": 200
  }'
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (no auth) |
| `/health/detailed` | GET | Rich status for dashboard probing |
| `/v1/models` | GET | Lists available models |
| `/v1/chat/completions` | POST | OpenAI-compatible chat (stateless) |
| `/v1/responses` | POST | Stateful responses (via `previous_response_id`) |
| `/v1/capabilities` | GET | Machine-readable API capabilities |
| `/api/sessions` | GET/POST | List/create Hermes sessions |
| `/api/sessions/{id}/messages` | GET | Session message history |
| `/v1/runs` | POST | Start a run (async, returns run_id) |
| `/v1/runs/{id}` | GET | Check run status |
| `/v1/runs/{id}/stop` | POST | Interrupt a running agent |

### Starting the gateway as a persistent service

For production use, start the gateway in the background:

```bash
# Via SSH from another machine
ssh <user>@<host> 'nohup hermes gateway run --accept-hooks > /tmp/hermes-gateway.log 2>&1 &'

# Or use a launchd plist on macOS for auto-restart
```

### Stopping the gateway

```bash
pkill -f "hermes gateway run"
```

### Usage from this Hermes

Once the API Server is running, I (this Hermes) can query mb14's Hermes by sending HTTP requests to the API. The user simply says "Ask mb14 to X" and I handle the backend call.

---

## 7. Usage Guide

### Quick reference

| Task | Command / Action |
|------|-----------------|
| Check if mb14 is online | `tailscale status` (look for `-` status) |
| Restart mb14 gateway | `ssh asadpreuss-dodhy@192.168.1.200 'pkill -f "hermes gateway run"; hermes gateway run --accept-hooks &'` |
| Check mb14 API health | `curl http://192.168.1.200:8642/health` |
| Test SSH connection | `ssh asadpreuss-dodhy@192.168.1.200 "echo OK"` |
| Restart Tailscale | `pkill tailscaled && ... tailscaled ... &` |
| Reload MCP tools | `/reload-mcp` (in Hermes session) |

### Working across profiles

The MCP server `mb14` is configured in the **team-manager** profile. If you switch profiles and need access:

```bash
hermes profile use <name>
hermes mcp add mb14 --command ssh --args asadpreuss-dodhy@192.168.1.200 \
  /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes \
  mcp serve --accept-hooks
```

---

## 8. Troubleshooting

### Tailscale

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `tailscale` command not found | Not installed | `brew install tailscale` |
| Socket not found | Daemon not running | Restart with absolute paths |
| `bind: permission denied` | Default socket needs root | Use `--socket` with user-writable path |
| Device shows `offline` | Machine asleep or disconnected | Wake it, check tailscale status on that machine |
| Ping fails | ICMP blocked in userspace mode | Normal — test with TCP instead (`curl :8642/health`) |

### SSH

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Connection timed out` | Remote Login off, or wrong IP | Enable Remote Login on mb14; check LAN/Tailscale IP |
| `Permission denied` | Wrong key or username | Verify SSH key in `~/.ssh/authorized_keys` on mb14 |
| `Too many authentication failures` | Wrong keys tried | Use `ssh -o IdentitiesOnly=yes` |

### MCP Server

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Failed to connect: Connection closed` | SSH path issue | Use full venv path, not `~/.local/bin/hermes` |
| Tools not appearing | Session needs refresh | `/reload-mcp` or `/reset` |
| "No MCP servers configured" | Not added to this profile | Check profile with `hermes profile show` |

### API Server

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Invalid API key` | Wrong key in request | Check `API_SERVER_KEY` in mb14's `.env` |
| Health OK but auth fails | Gateway needs restart after .env change | `pkill -f "hermes gateway run"` then restart |
| No response / timeout | Gateway may have crashed | On mb14: `hermes gateway run --accept-hooks` |
| Command approval blocks | Non-interactive API needs approval bypass | Run `hermes gateway run --accept-hooks` or set `approvals.mode: off` (use with caution!) |

---

## 9. Security Notes

- **Tailscale userspace networking** is less privileged than kernel mode — no root needed, but also no kernel-level traffic filtering. All traffic is still encrypted end-to-end via WireGuard.
- **API Server key** should be a strong random string. Store it in `.env` (not `config.yaml`). The `.env` file should have restricted permissions (`chmod 600`).
- **SSH keys** grant full shell access to the remote machine. Guard them carefully.
- **MCP over SSH** has the same access as the SSH user — it can run any command on mb14.
- **LAN traffic** between the machines on `192.168.x.x` is unencrypted at the network level. For sensitive operations, use the Tailscale IP (`100.x.x.x`) which is WireGuard-encrypted.
- **The API Server default host is `127.0.0.1`** (localhost-only). We set it to `0.0.0.0` to allow LAN access. If only Tailscale access is needed, bind it to mb14's Tailscale IP for better security.
- **Command approval** on mb14 can block non-interactive API calls. Either run gateway with `--accept-hooks` (which auto-approves shell hooks) or keep approvals on and be prepared to approve requests on mb14's screen.
- **Profile isolation** means the MCP server configuration is specific to the team-manager profile on mb16. Other profiles won't have access unless explicitly configured.
