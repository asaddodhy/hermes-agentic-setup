# Hermes Agentic Setup

> **Created:** June 15, 2026
> **Author:** Hermes Agent (mb16 — this machine)
> **Last updated:** June 17, 2026
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

## Kits — Complete Inventory

All kits are under `kits/`. Each is a self-contained `kit.md` with YAML frontmatter + step-by-step workflow. Run them in order for a full restoration.

| # | Kit | What it does | Dependencies | Backup status |
|---|-----|-------------|--------------|--------------|
| 1 | **[Hermes Install](kits/hermes-install/kit.md)** | Install Hermes Agent v0.16.0, Python 3.11, Tirith | — | ✅ Can reinstall from pip |
| 2 | **[Hermes Profiles](kits/hermes-profiles/kit.md)** | Create all 3 profiles (default, novelist, team-manager) with configs, skills, SOUL.md, AGENTS.md | Kit 1 | ✅ Tarball-able |
| 3 | **[Model Providers](kits/model-providers/kit.md)** | Set up Copilot (gpt-5-mini) and OpenCode Zen (deepseek-v4-flash-free), auth, .env | Kit 1 | 🔶 Needs re-auth |
| 4 | **[Novel-OS](kits/novel-os/kit.md)** | Install Novel-OS writing platform, venv, story state, novelist profile integration | Kit 1, 2 | ✅ Tarball-able (350 MB) |
| 5 | **[Tailscale Userspace](kits/tailscale-userspace/kit.md)** | Tailscale daemon in userspace mode, mesh between mb16 ↔ mb14 | — | 🔶 Needs re-auth |
| 6 | **[SSH Key Auth](kits/ssh-key-auth/kit.md)** | SSH key pair, deploy to mb14, passwordless login | Kit 5 | ✅ Tarball-able |
| 7 | **[MCP Remote Bridge](kits/hermes-mcp-bridge/kit.md)** | MCP server `mb14` in team-manager profile, 10 messaging tools | Kits 5, 6 | ✅ Tarball-able |
| 8 | **[API Server](kits/hermes-api-server/kit.md)** | Remote Hermes API server on mb14, OpenAI-compatible HTTP | Kits 5, 6 | 🔶 Needs re-deploy |
| 9 | **[Security Hardening](kits/security-hardening/kit.md)** | Tirith custom rules, smart approvals, secure-credentials skill | Kit 1 | ✅ Tarball-able |

### What each icon means for restoration:
- ✅ **Tarball-able** — files can be copied from the backup archive directly
- 🔶 **Needs re-auth or re-deploy** — requires interactive setup (paste token, run auth flow, etc.)

---

## Restoration Order

For a complete restoration on a new machine, run kits in this order:

```
 1. hermes-install        (foundation: Hermes + Python)
 2. hermes-profiles       (structure: 3 profiles, configs, skills, personalities)
 3. model-providers       (access: Copilot auth, API keys)
 4. novel-os              (writing: Novel-OS install + integration)
 5. tailscale-userspace   (mesh: VPN daemon)
 6. ssh-key-auth          (access: passwordless SSH)
 7. hermes-mcp-bridge     (tools: remote messaging)  ← requires 5+6
 8. hermes-api-server     (agent: full remote API)    ← requires 5+6
 9. security-hardening    (safety: lock it down)
```

Kits 7 and 8 can be done independently once 5+6 are in place. Kit 4 is optional if you don't need novel writing.

---

## Connection Paths

| Path | When to use |
|------|-------------|
| `asadpreuss-dodhy@192.168.1.200` | LAN (best performance, same network) |
| `asadpreuss-dodhy@100.97.232.91` | Tailscale (encrypted end-to-end, works across networks) |

---

## Quick Reference

| Task | Command |
|------|---------|
| Check mb14 online | `tailscale --socket ~/.hermes/tailscale.sock status` (look for `-`) |
| Test SSH connection | `ssh asadpreuss-dodhy@192.168.1.200 "echo OK"` |
| Restart mb14 gateway | `ssh asadpreuss-dodhy@192.168.1.200 'pkill -f "hermes gateway run"; hermes gateway run --accept-hooks &'` |
| Check mb14 API health | `curl http://192.168.1.200:8642/health` |
| Restart Tailscale | `pkill tailscaled && /opt/homebrew/opt/tailscale/bin/tailscaled --tun=userspace-networking --state=$HOME/.hermes/tailscale-state.json --socket=$HOME/.hermes/tailscale.sock > /tmp/tailscaled.log 2>&1 &` |
| Reload MCP tools | `/reload-mcp` (in Hermes session) |
| Create backup | `./scripts/hermes-backup.sh` or invoke the `hermes-repo-backup` skill |

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

For full security hardening, run **Kit 9** (`kits/security-hardening/`).

---

## Backup & Restore

### Making a backup

Invoke the `hermes-repo-backup` skill in a Hermes session, or run the backup script directly:

```bash
./scripts/hermes-backup.sh
```

This creates a tarball at:
- `/Volumes/Seagate_Backup_Plus_Drive/NAS/Hermes Backup/` (if network drive is connected)
- `~/Documents/Hermes Backup/` (fallback, with a notification)

For full restoration instructions, see **[MASTER-RESTORATION.md](MASTER-RESTORATION.md)**.
