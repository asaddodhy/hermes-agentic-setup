---
name: hermes-networking
description: "End-to-end cross-machine Hermes networking — Tailscale userspace VPN mesh, SSH key-based auth, MCP remote bridge, and remote API server. Orchestrates the sequence: mesh → access → tools → API."
version: 1.0.0
author: dodhya
models:
  primary: any
services:
  tailscale:
    required: true
    description: "VPN mesh for cross-machine connectivity. Userspace (no-root) mode with custom socket/state paths."
    setup: "See sub-kit: kits/tailscale-userspace/kit.md"
  ssh:
    required: true
    description: "Passwordless SSH key authentication from control machine to remote worker nodes."
    setup: "See sub-kit: kits/ssh-key-auth/kit.md"
  hermes-mcp:
    required: false
    description: "MCP remote bridge — local agent talks to remote gateway via SSH stdio, gaining 10+ messaging tools."
    setup: "See sub-kit: kits/hermes-mcp-bridge/kit.md"
  hermes-api:
    required: false
    description: "OpenAI-compatible HTTP API on the remote machine — programmatic access from scripts, SDKs, or automation."
    setup: "See sub-kit: kits/hermes-api-server/kit.md"
parameters:
  machines.local: "mb16 (dodhya, 100.120.204.56)"
  machines.remote: "mb14 (asadpreuss-dodhy, 100.97.232.91, 192.168.1.200)"
  tailscale.userspace.socket: ~/.hermes/tailscale.sock
  tailscale.userspace.state: ~/.hermes/tailscale-state.json
  api.port: 8642
  mcp.profile: team-manager
environment:
  os: [macos]
  homebrew: true
  hermes_version: ">=0.1.0"
dependencies:
  - "Two macOS machines (local control node + remote worker node)"
  - "Hermes Agent installed on both machines"
  - "Homebrew on both machines"
  - "Same Tailscale tailnet for encrypted fallback"
  - "Remote machine must have Remote Login (SSH) enabled in System Settings → General → Sharing"
security:
  secrets_stored:
    - name: API Server key (optional)
      location: "~/.hermes/.env on remote machine"
      sensitive: true
      note: "Generated once, stored in .env, chmod 600. Treat as a password — any HTTP client with this key can access the remote agent."
  trust_boundaries:
    - "SSH keys grant full shell access to the remote user. Protect the private key on the control machine."
    - "MCP over SSH gives the local agent the same access as the SSH user on the remote machine."
    - "API Server key should be rotated if compromised (regenerate and update .env)."
  known_threats:
    - "LAN traffic (192.168.x.x) is unencrypted at the network level — use Tailscale IP (100.x.x.x) for sensitive operations across untrusted networks."
    - "Tailscale userspace mode means no system-level tun interface — the local machine cannot reach its own Tailscale IP; this is expected and safe."
tags: [networking, cross-machine, multi-agent, mesh, tailscale, ssh, mcp, api-server, orchestration]
src:
  fileManifest: []
  note: "This is an umbrella/orchestrator kit. It references sub-kits (tailscale-userspace, ssh-key-auth, hermes-mcp-bridge, hermes-api-server) that contain the detailed setup steps and source files."
---

# Hermes Networking — Cross-Machine Setup Kit

## Goal

Set up **full cross-machine networking** between two Hermes Agent instances, enabling:

- **Mesh VPN** — encrypted tunnel between machines via Tailscale (no root, no GUI)
- **SSH key auth** — passwordless access from control node to remote worker nodes
- **MCP remote bridge** — local agent can invoke tools on the remote machine (send messages, read conversations, etc.)
- **Remote API server** — programmatic access to the remote Hermes agent via OpenAI-compatible HTTP API

This is the **orchestrator kit** — it sequences the four sub-kits in dependency order and provides the big-picture view.

---

## When to Use

- **Fresh two-machine setup** — you have two Macs and want to connect them for multi-agent orchestration
- **Restoring after system wipe** — re-establish the full networking stack from scratch
- **Adding a new remote node** to an existing Hermes mesh
- **Before using any cross-machine feature** — MCP tools, remote API, or multi-instance delegation
- **Auditing network connectivity** — verify that the full stack (mesh → auth → tools → API) is healthy

---

## Setup

### Prerequisites

| Requirement | Check |
|-------------|-------|
| Two macOS machines | Local (control) + Remote (worker) |
| Hermes Agent installed on both | `hermes --version` |
| Homebrew on both | `brew --version` |
| Same tailnet for Tailscale | Shared Tailscale account |
| SSH enabled on remote | System Settings → General → Sharing → Remote Login |

### Architecture

```
┌─────────────────┐     Tailscale (encrypted)     ┌──────────────────┐
│  mb16 (CONTROL) │◄══════════════════════════════►│  mb14 (REMOTE)   │
│                 │     SSH (key auth)              │                   │
│  Hermes Agent   │───────────────────────────────►│  Hermes Agent     │
│                 │     MCP (SSH stdio)             │  Gateway (:8642)  │
│  MCP Client ────┤───────────────────────────────►│  MCP Server       │
│                 │     HTTP API                    │  (SSH stdio)      │
│  curl / SDK ────┤───────────────────────────────►│  API (:8642)      │
└─────────────────┘                                └───────────────────┘
```

### Connection paths

| Transport | Address | Encrypted | Notes |
|-----------|---------|:---------:|-------|
| **LAN** | `192.168.1.200` | ❌ | Best performance, same network |
| **Tailscale** | `100.97.232.91` | ✅ | End-to-end WireGuard, works across subnets |

---

## Kit Sequence

The four sub-kits **must** be run in this order:

```
 1. tailscale-userspace  │  Mesh layer  │  Encrypted tunnel
 2. ssh-key-auth         │  Auth layer  │  Passwordless access
 3. hermes-mcp-bridge    │  Tools layer │  Remote MCP tools (optional)
 4. hermes-api-server    │  API layer   │  Remote HTTP API (optional)
```

### Kit 1 — Tailscale Userspace

Establishes the encrypted mesh VPN between machines.

```bash
# Reference: kits/tailscale-userspace/kit.md
# Source files: kits/tailscale-userspace/src/
#   - io.tailscale.userspace.plist → ~/Library/LaunchAgents/
#   - tailscale-helper.sh → ~/.hermes/bin/

# Quick start (see kit for full steps):
brew install tailscale
/opt/homebrew/opt/tailscale/bin/tailscaled \
  --tun=userspace-networking \
  --state="$HOME/.hermes/tailscale-state.json" \
  --socket="$HOME/.hermes/tailscale.sock" &

tailscale --socket="$HOME/.hermes/tailscale.sock" up
```

**Verify:** `tailscale --socket ~/.hermes/tailscale.sock status` shows both machines.

---

### Kit 2 — SSH Key Auth

Establishes passwordless SSH from control → remote machine.

```bash
# Reference: kits/ssh-key-auth/kit.md

# Generate key pair (if needed):
ssh-keygen -t ed25519 -C "hermes-mesh-$(date +%Y%m%d)" -f ~/.ssh/hermes_mesh

# Deploy to remote:
ssh-copy-id -i ~/.ssh/hermes_mesh.pub asadpreuss-dodhy@192.168.1.200

# Test:
ssh asadpreuss-dodhy@192.168.1.200 "echo OK"
# → OK
```

**Verify:** Both LAN IP (`192.168.1.200`) and Tailscale IP (`100.97.232.91`) return `OK`.

---

### Kit 3 — MCP Remote Bridge (Optional)

Gives the local agent access to remote Hermes tools (send messages, read conversations, list contacts, etc.) via the MCP protocol over SSH.

```bash
# Reference: kits/hermes-mcp-bridge/kit.md

# Add MCP server entry to the active Hermes profile's config.yaml:
hermes config set mcp_servers.remote_mb14.type stdio
hermes config set mcp_servers.remote_mb14.command ssh
hermes config set 'mcp_servers.remote_mb14.args=["asadpreuss-dodhy@192.168.1.200", "hermes", "mcp", "serve", "--accept-hooks"]'

# Reload MCP tools:
/reload-mcp
```

**Verify:** Run `/tools` in the Hermes session — should show remote tools (`send_message`, `read_messages`, `list_conversations`, etc.).

---

### Kit 4 — Remote API Server (Optional)

Exposes the remote Hermes agent via OpenAI-compatible HTTP API on port 8642.

```bash
# Reference: kits/hermes-api-server/kit.md

# On the remote machine (mb14), via SSH:
ssh asadpreuss-dodhy@192.168.1.200 \
  "pkill -f 'hermes gateway run' 2>/dev/null; \
   nohup hermes gateway run --accept-hooks \
   > ~/.hermes/gateway.log 2>&1 &"

# Verify from local:
curl http://192.168.1.200:8642/health
# → {"status":"ok","version":"...","model":"..."}
```

**Verify:** `curl http://192.168.1.200:8642/health` returns a JSON health response.

---

## Full Automation Script

For a complete head-to-tail networking setup, run this from the control machine (mb16):

```bash
#!/bin/bash
# full-networking-setup.sh — Hermes Networking Kit (umbrella bootstrap)
# Prerequisites: brew, Hermes Agent, remote SSH enabled
set -euo pipefail

LOCAL_USER="dodhya"
REMOTE_USER="asadpreuss-dodhy"
REMOTE_LAN="192.168.1.200"
REMOTE_TSN="100.97.232.91"
KITS_DIR="$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)/.."

echo "=== Hermes Networking — Full Bootstrap ==="

# Step 1: Tailscale
echo ""
echo "[1/4] Tailscale userspace mesh..."
if ! tailscale --socket ~/.hermes/tailscale.sock status &>/dev/null; then
  echo "  Installing/starting Tailscale..."
  brew install tailscale 2>/dev/null || true
  pkill tailscaled 2>/dev/null || true
  /opt/homebrew/opt/tailscale/bin/tailscaled \
    --tun=userspace-networking \
    --state="$HOME/.hermes/tailscale-state.json" \
    --socket="$HOME/.hermes/tailscale.sock" &
  sleep 2
  tailscale --socket="$HOME/.hermes/tailscale.sock" up
fi
echo "  ✅ Tailscale: $(tailscale --socket ~/.hermes/tailscale.sock ip -4)"

# Step 2: SSH key
echo ""
echo "[2/4] SSH key auth..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$REMOTE_USER@$REMOTE_LAN" "echo OK" &>/dev/null; then
  echo "  Deploying SSH key..."
  if [ ! -f ~/.ssh/hermes_mesh ]; then
    ssh-keygen -t ed25519 -f ~/.ssh/hermes_mesh -N "" -C "hermes-mesh"
  fi
  ssh-copy-id -i ~/.ssh/hermes_mesh.pub "$REMOTE_USER@$REMOTE_LAN"
fi
echo "  ✅ SSH: $(ssh -o BatchMode=yes $REMOTE_USER@$REMOTE_LAN 'hostname -s')"

# Step 3: MCP bridge
echo ""
echo "[3/4] MCP remote bridge (optional)..."
hermes config set 'mcp_servers.remote_mb14.type=stdio' 2>/dev/null || true
hermes config set 'mcp_servers.remote_mb14.command=ssh' 2>/dev/null || true
hermes config set 'mcp_servers.remote_mb14.args=["asadpreuss-dodhy@192.168.1.200", "hermes", "mcp", "serve", "--accept-hooks"]' 2>/dev/null || true
echo "  ✅ MCP server 'remote_mb14' configured"
echo "  ⚡ Run /reload-mcp in Hermes to activate"

# Step 4: API server
echo ""
echo "[4/4] Remote API server (optional)..."
ssh "$REMOTE_USER@$REMOTE_LAN" \
  "pkill -f 'hermes gateway run' 2>/dev/null || true; \
   nohup hermes gateway run --accept-hooks \
   > ~/.hermes/gateway.log 2>&1 &"
sleep 2
echo "  ✅ API server: curl http://$REMOTE_LAN:8642/health"
curl -s "http://$REMOTE_LAN:8642/health" | head -1

echo ""
echo "=== Hermes Networking — Bootstrap Complete ==="
```

Save as `kits/hermes-networking/full-networking-setup.sh` and run with `bash full-networking-setup.sh`.

---

## Constraints

- **Order matters** — SSH auth requires Tailscale to be functional (for Tailscale IP fallback). MCP bridge requires SSH. API server is standalone once SSH works.
- **Tailscale userspace limits** — The machine cannot reach its own Tailscale IP. All connectivity tests from the control machine must use the **remote** IP, not the local one.
- **API server binds to `127.0.0.1` by default** — To access from other machines, either (1) bind to `0.0.0.0`, (2) add an SSH tunnel, or (3) bind to the Tailscale IP. Binding to `0.0.0.0` without an API key is a security risk.
- **MCP tools depend on profile** — The MCP server entry is per-profile. If you add it to `team-manager`, it won't appear in `default` or `novelist` profiles.
- **TMUX sessions on the remote** — The gateway process runs in `nohup` mode and may die on TMUX session close. Use a persistent TMUX session or `launchd` plist for the API server.
- **Tailscale state loss** — If `~/.hermes/tailscale-state.json` is lost, you must re-authenticate with `tailscale up`. The `security-hardening` kit backs it up.

---

## Verification

```text
[ ] Tailscale running:    tailscale --socket ~/.hermes/tailscale.sock status → both machines visible
[ ] SSH key auth (LAN):   ssh -o BatchMode=yes asadpreuss-dodhy@192.168.1.200 "echo OK" → OK
[ ] SSH key auth (TSN):   ssh -o BatchMode=yes asadpreuss-dodhy@100.97.232.91 "echo OK" → OK
[ ] MCP tools loaded:     In Hermes session, run /tools → remote tools visible
[ ] API health:           curl http://192.168.1.200:8642/health → {"status":"ok",...}
[ ] API via Tailscale:    curl http://100.97.232.91:8642/health → {"status":"ok",...}
[ ] Gateway process:      ssh asadpreuss-dodhy@192.168.1.200 "pgrep -f 'hermes gateway run'" → PID
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `tailscale status` shows `-` or nothing | Tailscale daemon stopped | Restart: `pkill tailscaled && ...tailscaled --tun=userspace-networking ... &` |
| `ssh: connect to host 192.168.1.200: Connection refused` | Remote SSH not enabled or remote offline | Check System Settings → General → Sharing → Remote Login; ping the remote |
| `ssh: Permission denied (publickey)` | Key not deployed | Re-run `ssh-copy-id` |
| MCP tools not showing after `/reload-mcp` | Config error or remote gateway not running | Check `hermes config get mcp_servers`; test SSH then command manually |
| `curl: Connection refused` on API endpoint | Gateway not started on remote | SSH in and check `pgrep -f 'hermes gateway run'`; re-run the startup command |
| `curl: exit code 28` (timeout) to Tailscale IP | Local machine can't reach its own Tailscale IP (userspace mode) | Test from another device on the tailnet, or use LAN IP instead |
| MCP server shows as disconnected | Remote Hermes session died | SSH in and start a Hermes session: `hermes` (any command keeps the agent alive) |
