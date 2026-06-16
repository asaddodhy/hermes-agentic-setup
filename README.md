# Hermes Multi-Machine Setup

> **Created:** June 15, 2026
> **Author:** Hermes Agent (mb16 — this machine)
> **Last updated:** June 16, 2026
> **Machines:**
> - **mb16** — MacBook, user `dodhya`, Tailscale IP `100.120.204.56`
> - **mb14** — MacBook (N719HT), user `asadpreuss-dodhy`, Tailscale IP `100.97.232.91`, LAN IP `192.168.1.200`
> - Also on tailnet: `pixel-10-pro-xl` (Android, offline)

---

## Architecture

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

Two connection methods:

| Method | What it provides | Transport |
|--------|-----------------|-----------|
| **MCP Server** | mb14's messaging gateway (tools: send/read messages, list conversations, etc.) | SSH stdio |
| **API Server** | mb14's full agent via OpenAI-compatible HTTP API | HTTP (`:8642`) |

---

## Prerequisites

| Required | Details |
|----------|---------|
| macOS | Both machines (other OS supported but not tested) |
| Homebrew | `brew install tailscale` |
| Hermes Agent | Installed on both machines |
| Tailscale account | Free tier works |

---

## Quick Reference

| Task | Command |
|------|---------|
| Check mb14 online | `tailscale --socket ~/.hermes/tailscale.sock status` (look for `-`) |
| Restart mb14 gateway | `ssh asadpreuss-dodhy@192.168.1.200 'pkill -f "hermes gateway run"; hermes gateway run --accept-hooks &'` |
| Check mb14 API health | `curl http://192.168.1.200:8642/health` |
| Test SSH connection | `ssh asadpreuss-dodhy@192.168.1.200 "echo OK"` |
| Restart Tailscale | `pkill tailscaled && /opt/homebrew/opt/tailscale/bin/tailscaled --tun=userspace-networking --state=/Users/dodhya/.hermes/tailscale-state.json --socket=/Users/dodhya/.hermes/tailscale.sock > /tmp/tailscaled.log 2>&1 &` |
| Reload MCP tools | `/reload-mcp` (in Hermes session) |

---

## Kits — Reusable Workflow Blueprints

The detailed setup is broken into standalone kits under `kits/`. Each kit is a self-contained `kit.md` with structured frontmatter (models, services, parameters) and a step-by-step workflow body. Run them individually or in sequence to reproduce any part of the setup.

| # | Kit | What it installs | Dependencies |
|---|-----|-----------------|--------------|
| 1 | **[Tailscale Userspace for Agent Mesh](kits/tailscale-userspace/kit.md)** | Tailscale daemon in userspace mode, `~/.hermes/tailscale.sock`, persistent state | — |
| 2 | **[SSH Key Auth for Cross-Machine Agents](kits/ssh-key-auth/kit.md)** | SSH key pair, `authorized_keys` on remote, passwordless login test | Kit 1 |
| 3 | **[Hermes MCP Remote Bridge](kits/hermes-mcp-bridge/kit.md)** | MCP server `mb14` in profile config, 10 messaging tools | Kits 1, 2 |
| 4 | **[Hermes API Server](kits/hermes-api-server/kit.md)** | `.env` API key, gateway launch, health check, chat completion test | Kits 1, 2 |
| 5 | **[Security Hardening Suite](kits/security-hardening/kit.md)** | Tirith custom rules policy, smart approvals, secure-credentials skill | — |

Each kit follows the **Journey Kit** format (`kit.md` with YAML frontmatter + markdown body) so you can run them agent-assisted — point your agent at a `kit.md` and it will execute the workflow.

---

## Setup Order

For a fresh machine, run kits in this order:

```
1. tailscale-userspace   (foundation: VPN mesh)
2. ssh-key-auth          (access: passwordless login)
3. hermes-mcp-bridge     (tools: remote messaging)
   hermes-api-server     (agent: full remote agent)   ← either or both
5. security-hardening    (safety: lock it down)
```

Kits 3 and 4 can be done independently once 1+2 are in place.

---

## Connection Paths

| Path | When to use |
|------|-------------|
| `asadpreuss-dodhy@192.168.1.200` | LAN (best performance, same network) |
| `asadpreuss-dodhy@100.97.232.91` | Tailscale (encrypted end-to-end, works across networks) |

---

## Migrating to Another Machine

```bash
# 1. Copy the Tirith policy
mkdir -p ~/.tirith
cp path/to/backup/.tirith/policy.yaml ~/.tirith/

# 2. Set approvals mode
hermes config set approvals.mode smart

# 3. Copy the skill
cp -r path/to/backup/.hermes/skills/software-development/secure-credentials \
  ~/.hermes/skills/software-development/secure-credentials

# 4. Verify Tirith
~/.hermes/bin/tirith policy validate
```

Or better — run the relevant kit from `kits/`.

---

## Security Principles

- **Tailscale userspace networking** — no root needed, end-to-end WireGuard encryption
- **API Server key** — strong random string in `.env` (not config.yaml), `chmod 600`
- **SSH keys** — full shell access to remote machine; guard them carefully
- **MCP over SSH** — same access as SSH user; it can run any command on mb14
- **LAN vs Tailscale** — use `100.x.x.x` IP for sensitive operations (encrypted); `192.168.x.x` is unencrypted at the network level
- **API Server binding** — default `127.0.0.1` (localhost); set to Tailscale IP instead of `0.0.0.0` when possible
- **Command approval** — run gateway with `--accept-hooks` to auto-approve shell hooks, or keep approvals on
- **Profile isolation** — MCP server config lives in the profile it was added to; add it per-profile

For full security hardening, run **Kit 5** (`kits/security-hardening/`).
