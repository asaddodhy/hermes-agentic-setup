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

All kits are under `kits/`. Each is a self-contained `kit.md` with YAML frontmatter + step-by-step workflow. Run them in restoration order (see below) for a full setup.

<!-- KIT-TABLE:START -->
| # | Kit | What it does | Dependencies | Backup status |
|---|---|---|---|---|
| 1 | **[hermes-api-server](kits/hermes-api-server/kit.md)** | Deploy a remote Hermes Agent API server exposing an OpenAI-compatible HTTP AP... | | |
| 2 | **[hermes-install](kits/hermes-install/kit.md)** | Install Hermes Agent from scratch on a new macOS machine — pip, pipx, or Home... | | |
| 3 | **[hermes-mcp-remote-bridge](kits/hermes-mcp-bridge/kit.md)** | Bridge two Hermes Agent instances over SSH stdio via the MCP protocol — givin... | | |
| 4 | **[hermes-profiles](kits/hermes-profiles/kit.md)** | Set up all 3 Hermes profiles (default, novelist, team-manager) with their uni... | | |
| 5 | **[model-providers](kits/model-providers/kit.md)** | Document and restore all Hermes model provider configurations — Copilot (GitH... | | |
| 6 | **[novel-os](kits/novel-os/kit.md)** | Install, restore, and integrate Novel-OS — a multi-agent fiction writing fram... | | |
| 7 | **[security-hardening-suite](kits/security-hardening/kit.md)** | Lock down a Hermes Agent with Tirith custom rules, smart approvals mode, and ... | | |
| 8 | **[ssh-key-auth](kits/ssh-key-auth/kit.md)** | Set up SSH key-based authentication between two machines for cross-machine He... | | |
| 9 | **[tailscale-userspace](kits/tailscale-userspace/kit.md)** | Set up Tailscale in userspace (no-root) mode for cross-machine Hermes agent m... | | |
<!-- KIT-TABLE:END -->

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
