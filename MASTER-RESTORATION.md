# Master Restoration Checklist

> Use this checklist when setting up Hermes on a new machine or restoring from backup.
> Run the kits in order — each kit's `kit.md` has full step-by-step instructions.

## Prerequisites

- [ ] macOS machine (Apple Silicon or Intel)
- [ ] Internet connection
- [ ] Backup tarball accessible (from network drive or `~/Documents/Hermes Backup/`)
- [ ] Your API keys / credentials ready (Copilot, OpenCode Zen, etc.)
- [ ] Remote machine (mb14) powered on and on the same network

---

## Phase 1: Foundation

### □ Kit 1 — Hermes Install

**Goal:** Hermes Agent running on the new machine.

- [ ] Python 3.11 installed
- [ ] `pip3 install hermes-agent` completed
- [ ] `~/.local/bin/hermes` works (`hermes --version`)
- [ ] `~/.local/bin` is in PATH
- [ ] Initial config created (`hermes setup` or from backup)

**Kit file:** `kits/hermes-install/kit.md`

---

### □ Kit 2 — Profile Setup

**Goal:** All 3 Hermes profiles (default, novelist, team-manager) created with configs, skills, and personalities.

**From backup tarball:**
- [ ] Copy `config.yaml` → `~/.hermes/config.yaml`
- [ ] Copy `SOUL.md` → `~/.hermes/SOUL.md`
- [ ] Copy `skills/` → `~/.hermes/skills/` (50+ skills)
- [ ] Copy `memories/` → `~/.hermes/memories/`
- [ ] Copy `kanban.db` → `~/.hermes/kanban.db`
- [ ] Create novelist profile: `hermes profile create novelist`
- [ ] Copy novelist profile files from tarball → `~/.hermes/profiles/novelist/`
- [ ] Copy team-manager profile files from tarball → `~/.hermes/profiles/team-manager/`

**Verify each profile:**
- [ ] `hermes profile list` shows all 3 profiles
- [ ] `hermes profile switch novelist` works
- [ ] `hermes profile switch team-manager` works
- [ ] Profiles have their skills loaded

**Kit file:** `kits/hermes-profiles/kit.md`

---

## Phase 2: Access

### □ Kit 3 — Model Providers

**Goal:** Set up AI model providers so Hermes can respond.

**Copilot (for default profile):**
- [ ] Run `hermes model` → select GitHub Copilot
- [ ] Complete device code flow (open URL, paste code, authorize)
- [ ] Verify: `hermes auth list` shows copilot provider

**OpenCode Zen (for team-manager profile):**
- [ ] Add `OPENCODE_ZEN_API_KEY` to `~/.hermes/profiles/team-manager/.env`
- [ ] Switch to team-manager profile: `hermes profile switch team-manager`
- [ ] Set model: `hermes model` → select opencode-zen / deepseek-v4-flash-free

**General:**
- [ ] Test: Send a message in each profile — does the model respond?

**Kit file:** `kits/model-providers/kit.md`

---

### □ Kit 4 — Novel-OS

**Goal:** Novel writing platform installed and integrated with novelist profile.

- [ ] `git clone https://github.com/mrigankad/Novel-OS.git ~/novel-os/`
- [ ] Python venv created: `cd ~/novel-os && python3 -m venv .venv`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` configured (provider keys, StoryState path)
- [ ] Novelist profile updated:
  - [ ] `SOUL.md` copied from `kits/novel-os/src/SOUL.md`
  - [ ] `AGENTS.md` copied from `kits/novel-os/src/AGENTS.md`
  - [ ] Novel-OS skill installed: `cp -r kits/novel-os/src/SKILL.md ~/.hermes/profiles/novelist/skills/novel-os/`
- [ ] Test: Run `novel-os()` alias — does it work?

**Kit file:** `kits/novel-os/kit.md`

---

## Phase 3: Multi-Machine Mesh

### □ Kit 5 — Tailscale Userspace

**Goal:** VPN mesh between local machine and mb14.

- [ ] Tailscale installed via Homebrew
- [ ] Userspace daemon running: `tailscaled --tun=userspace-networking --state=~/.hermes/tailscale-state.json --socket=~/.hermes/tailscale.sock`
- [ ] Authenticated: `tailscale --socket ~/.hermes/tailscale.sock up`
- [ ] Launchd plist installed for auto-start on login
- [ ] verify: `tailscale --socket ~/.hermes/tailscale.sock status`
- [ ] Can see mb14 (`100.97.232.91`)

**Kit file:** `kits/tailscale-userspace/kit.md`

---

### □ Kit 6 — SSH Key Auth

**Goal:** Passwordless SSH access to mb14.

- [ ] SSH key generated: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519`
- [ ] Key deployed to mb14: `ssh-copy-id asadpreuss-dodhy@192.168.1.200`
- [ ] Test passwordless: `ssh asadpreuss-dodhy@192.168.1.200 "echo OK"`
- [ ] `~/.ssh/config` has `Host mb14` block (LAN) and `Host mb14-ts` block (Tailscale)
- [ ] Tailscale route tested: `ssh asadpreuss-dodhy@100.97.232.91 "echo OK"`

**Kit file:** `kits/ssh-key-auth/kit.md`

---

## Phase 4: Remote Access

### □ Kit 7 — Hermes MCP Bridge

**Goal:** Remote Hermes tools available via MCP in team-manager profile.

- [ ] Remote Hermes is installed and working on mb14
- [ ] MCP server `mb14` configured in team-manager `config.yaml`:
  - Command: `ssh`
  - Args: `asadpreuss-dodhy@192.168.1.200 /path/to/hermes mcp serve --accept-hooks`
- [ ] MCP server enabled (field set to true)
- [ ] In Hermes session: `/reload-mcp`
- [ ] Verify: MCP tools appear (10 messaging tools)

**Kit file:** `kits/hermes-mcp-bridge/kit.md`

---

### □ Kit 8 — API Server

**Goal:** Remote Hermes API accessible over HTTP for programmatic use.

- [ ] Random API key generated and placed in mb14's `.env`
- [ ] Gateway started on mb14: `hermes gateway run --accept-hooks`
- [ ] Port 8642 bound to localhost (or Tailscale IP)
- [ ] Health check: `curl http://192.168.1.200:8642/health` → OK
- [ ] Chat completion test: `curl -X POST http://192.168.1.200:8642/v1/chat/completions -H ...`
- [ ] Auto-restart configured (launchd or tmux on mb14)

**Kit file:** `kits/hermes-api-server/kit.md`

---

## Phase 5: Security

### □ Kit 9 — Security Hardening

**Goal:** Lock down every profile with credential scanning and security policies.

- [ ] Tirith policy installed: `cp src/.tirith/policy.yaml ~/.tirith/policy.yaml`
- [ ] Policy validated: `~/.hermes/bin/tirith policy validate`
- [ ] Test blocks: `sshpass -p test ssh host` → BLOCKED
- [ ] Test blocks: `curl -u user:pass http://...` → BLOCKED
- [ ] Test warns: `PASSWORD=xxx command` → WARNED
- [ ] Smart approvals enabled: `hermes config set approvals.mode smart` (for each profile)
- [ ] `secure-credentials` skill installed in all 3 profiles

**Kit file:** `kits/security-hardening/kit.md`

---

## Phase 6: Verification

### Final Smoke Tests

- [ ] **Default profile:** Send a message — does it respond?
- [ ] **Team-manager profile:** Send a message — does it respond?
- [ ] **Novelist profile:** Switch to novelist, load novel-os skill, test pipeline
- [ ] **MCP tools:** In team-manager profile, MCP tools from mb14 are available
- [ ] **API server:** Remote HTTP API responds
- [ ] **Tirith:** Security scanning active on all profiles
- [ ] **GitHub remote:** `git remote -v` in `~/hermes-agentic-setup` shows `asaddodhy/hermes-agentic-setup`

### Data to restore from tarball

**Check the backup tarball has:**
- [ ] `config.yaml` for all 3 profiles
- [ ] `SOUL.md` for novelist and team-manager
- [ ] `AGENTS.md` for novelist
- [ ] `.env` templates (user fills in actual secrets)
- [ ] `auth.json` per profile
- [ ] `memories/MEMORY.md` + `memories/USER.md`
- [ ] `kanban.db`
- [ ] `.tirith/policy.yaml`
- [ ] `skills/` for all profiles
- [ ] `~/.ssh/` keys
- [ ] `~/.ssh/config`
- [ ] `novel-os/` directory (350 MB)

---

## What CAN'T be automated

These need human interaction:

| Item | Why | When |
|------|-----|------|
| Copilot device code auth | OAuth flow needs browser + human | Kit 3 |
| Tailscale auth | Browser login from tailscale.com | Kit 5 |
| SSH to mb14 | Need to enter password once for `ssh-copy-id` | Kit 6 |
| API keys in `.env` | Secrets must be entered manually or restored from password manager | Kit 3, 4 |
| mb14 physical access | If ping fails, check mb14 is powered on and on network | Phase 3 |
| Novel-OS provider keys | Tokens for Anthropic/OpenAI/Gemini in `~/novel-os/.env` | Kit 4 |
