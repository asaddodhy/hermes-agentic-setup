---
name: hermes-profiles
description: >-
  Set up all 3 Hermes profiles (default, novelist, team-manager) with their
  unique configs, skills, SOUL.md, and AGENTS.md from the repo backup.
version: 1.0.0
author: dodhya
models:
  primary: ""
  required_models:
    - gpt-5-mini via copilot
    - deepseek-v4-flash-free via opencode-zen
services: {}
parameters:
  approvals.mode: smart
  agent.reasoning_effort: medium
environment:
  os: [macos]
  homebrew: false
  hermes_version: ">=0.1.0"
src:
  fileManifest:
    - path: src/profiles/default/config.yaml
      role: "Default profile config (573 lines, v29) — general-purpose catch-all"
      destination: ~/.hermes/config.yaml
    - path: src/profiles/default/SOUL.md
      role: "Default profile SOUL.md — empty persona template"
      destination: ~/.hermes/SOUL.md
    - path: src/profiles/default/skills/
      role: "All 50+ default skills across 21 categories"
      destination: ~/.hermes/skills/
    - path: src/profiles/default/.env
      role: "Default profile environment variables"
      destination: ~/.hermes/.env
    - path: src/profiles/default/auth.json
      role: "Default profile auth credentials"
      destination: ~/.hermes/auth.json
    - path: src/profiles/novelist/config.yaml
      role: "Novelist profile config (4 lines) — minimal profile for creative writing"
      destination: ~/.hermes/profiles/novelist/config.yaml
    - path: src/profiles/novelist/SOUL.md
      role: "Novelist profile SOUL.md — warm literary editor persona"
      destination: ~/.hermes/profiles/novelist/SOUL.md
    - path: src/profiles/novelist/AGENTS.md
      role: "Novelist profile AGENTS.md — Novel-OS integration guide"
      destination: ~/.hermes/profiles/novelist/AGENTS.md
    - path: src/profiles/novelist/skills/
      role: "Novelist skills — all creative/writing + novel-os + writing-tools-evaluation"
      destination: ~/.hermes/profiles/novelist/skills/
    - path: src/profiles/novelist/.env
      role: "Novelist profile environment variables (profile-specific)"
      destination: ~/.hermes/profiles/novelist/.env
    - path: src/profiles/novelist/auth.json
      role: "Novelist profile auth credentials"
      destination: ~/.hermes/profiles/novelist/auth.json
    - path: src/profiles/team-manager/config.yaml
      role: "Team-manager profile config (576 lines, v30) — MCP servers, gateway, kanban"
      destination: ~/.hermes/profiles/team-manager/config.yaml
    - path: src/profiles/team-manager/SOUL.md
      role: "Team-manager SOUL.md — full Team Manager persona (managerial, delegation)"
      destination: ~/.hermes/profiles/team-manager/SOUL.md
    - path: src/profiles/team-manager/skills/
      role: "Team-manager skills — devops, kanban, hermes-agent, mlops"
      destination: ~/.hermes/profiles/team-manager/skills/
    - path: src/profiles/team-manager/.env
      role: "Team-manager profile environment variables (436B)"
      destination: ~/.hermes/profiles/team-manager/.env
    - path: src/profiles/team-manager/auth.json
      role: "Team-manager profile auth credentials"
      destination: ~/.hermes/profiles/team-manager/auth.json
---

## Goal

Restore all 3 Hermes profiles — **default**, **novelist**, and **team-manager** — with their exact configurations, skills, SOUL.md personas, AGENTS.md instructions, and credential stores. Each profile is a fully isolated environment with its own memory, session history, model config, and skillset.

After this kit, you can switch between profiles with `hermes profile switch <name>` and each will behave exactly as it did on the original machine.

## When to Use

- **New machine migration** — apply these profiles to a fresh Hermes install
- **After `hermes reset` or data loss** — restore from the repo backup
- **Profile corruption** — one profile got borked; rebuild just that one
- **Cloning a setup** — replicate this 3-profile architecture on another machine

## Profile Overview

| Profile       | Config            | Skills                                     | Model                   | Persona                         | Gateway  |
|---------------|-------------------|--------------------------------------------|-------------------------|---------------------------------|----------|
| **default**   | 573 lines, v29    | 50+ skills across 21 categories            | gpt-5-mini (copilot)    | Template (empty, editable)      | Stopped  |
| **novelist**  | 4 lines (minimal) | Creative/writing + novel-os + writing-tools | Inherits fallback       | Warm literary editor, Novel-OS   | Stopped  |
| **team-manager** | 576 lines, v30 | Devops/kanban + hermes-agent + mlops       | deepseek-v4-flash-free (opencode-zen) | Managerial, delegation, verification | Running  |

All profiles share the same directory structure per profile root:
```
config.yaml          .env              auth.json
SOUL.md              AGENTS.md         state.db
memories/            skills/           cron/
hooks/               logs/             cache/
```

## What This Kit Restores

| Bundle | Contents | Size Notes |
|--------|----------|------------|
| **default config** | `~/.hermes/config.yaml` — v29, 573 lines | Full catch-all config |
| **default SOUL** | `~/.hermes/SOUL.md` — empty persona template | ~537 bytes |
| **default skills** | 21 categories, 50+ skills | ~2 MB |
| **default .env** | Profile-specific environment variables | Variable |
| **default auth.json** | Credential store | Variable |
| **novelist config** | `~/.hermes/profiles/novelist/config.yaml` — 4 lines | Minimal: reasoning_effort + approvals.mode |
| **novelist SOUL** | `~/.hermes/profiles/novelist/SOUL.md` — literary editor | ~1 KB |
| **novelist AGENTS.md** | `~/.hermes/profiles/novelist/AGENTS.md` — profile rules + Novel-OS | ~1 KB |
| **novelist skills** | 19 categories, 89+ skills including novel-os and writing-tools-evaluation | ~3 MB |
| **novelist .env** | Profile-specific env | ~24 KB |
| **novelist auth.json** | Profile-specific auth | ~664 bytes |
| **team-manager config** | `~/.hermes/profiles/team-manager/config.yaml` — v30, 576 lines | Full config with MCP, kanban, gateway, delegation |
| **team-manager SOUL** | `~/.hermes/profiles/team-manager/SOUL.md` — full manager persona | ~3.9 KB |
| **team-manager skills** | 18 categories, 78+ skills including hermes-agent and mlops | ~3 MB |
| **team-manager .env** | Profile-specific env | 436 bytes |
| **team-manager auth.json** | Profile-specific auth | ~1.2 KB |

## Steps

### Step 1: Verify Hermes is installed and has profile support

```bash
hermes version
hermes profile list
```

Expected output shows the `profile list` command available with columns: Profile, Model, Gateway, Alias, Distribution. If `profile` is not a recognized command, update Hermes first:

```bash
hermes update
```

### Step 2: Create the profile directory structure

Create the profile directories before restoring assets:

```bash
mkdir -p ~/.hermes/profiles/novelist/{skills,cron,hooks,logs,cache,memories}
mkdir -p ~/.hermes/profiles/team-manager/{skills,cron,hooks,logs,cache,memories,plugins,sessions,state-snapshots,bin,lsp,plans,sandboxes,skins,workspace}
```

> **Note:** The team-manager profile has additional subdirectories (`plugins/`, `sessions/`, `state-snapshots/`, `bin/`, `lsp/`, `plans/`, `sandboxes/`, `skins/`, `workspace/`) that the novelist profile doesn't need.

### Step 3: Register profiles with Hermes

```bash
hermes profile create novelist
hermes profile create team-manager
```

This registers the profiles in Hermes' internal registry. Verify:

```bash
hermes profile list
```

Expected output:
```
Profile          Model                        Gateway      Alias        Distribution
───────────────    ───────────────────────────    ───────────    ───────────    ────────────────────
 default          gpt-5-mini                   stopped      —            —
 novelist         —                            stopped      —            —
 team-manager     —                            stopped      —            —
```

### Step 4: Restore default profile assets

```bash
# Config
cp src/profiles/default/config.yaml ~/.hermes/config.yaml

# SOUL.md
cp src/profiles/default/SOUL.md ~/.hermes/SOUL.md

# .env and auth.json
cp src/profiles/default/.env ~/.hermes/.env
cp src/profiles/default/auth.json ~/.hermes/auth.json
chmod 600 ~/.hermes/.env ~/.hermes/auth.json

# Skills (recursive — catches all 21 categories, 50+ skills)
cp -a src/profiles/default/skills/* ~/.hermes/skills/
```

### Step 5: Restore novelist profile assets

```bash
# Config (4-line minimal)
cp src/profiles/novelist/config.yaml ~/.hermes/profiles/novelist/config.yaml

# Persona
cp src/profiles/novelist/SOUL.md ~/.hermes/profiles/novelist/SOUL.md
cp src/profiles/novelist/AGENTS.md ~/.hermes/profiles/novelist/AGENTS.md

# Credentials
cp src/profiles/novelist/.env ~/.hermes/profiles/novelist/.env
cp src/profiles/novelist/auth.json ~/.hermes/profiles/novelist/auth.json
chmod 600 ~/.hermes/profiles/novelist/.env ~/.hermes/profiles/novelist/auth.json

# Skills (19 categories including novel-os)
cp -a src/profiles/novelist/skills/* ~/.hermes/profiles/novelist/skills/
```

### Step 6: Restore team-manager profile assets

```bash
# Config (576 lines, v30)
cp src/profiles/team-manager/config.yaml ~/.hermes/profiles/team-manager/config.yaml

# Persona (3.9 KB full manager SOUL)
cp src/profiles/team-manager/SOUL.md ~/.hermes/profiles/team-manager/SOUL.md

# Credentials
cp src/profiles/team-manager/.env ~/.hermes/profiles/team-manager/.env
cp src/profiles/team-manager/auth.json ~/.hermes/profiles/team-manager/auth.json
chmod 600 ~/.hermes/profiles/team-manager/.env ~/.hermes/profiles/team-manager/auth.json

# Skills (18 categories including hermes-agent and mlops)
cp -a src/profiles/team-manager/skills/* ~/.hermes/profiles/team-manager/skills/
```

> **Key skill differences between profiles:**
> - **Default has** `red-teaming/` and `self-hosting/` skill categories that profile-specific profiles lack
> - **Novelist has** `novel-os/` skill category that no other profile has
> - **Novelist includes** `writing/writing-tools-evaluation/` skill
> - **Team-manager** has 6 `mlops/` sub-skills (vs 5 in default), has `hermes-agent/` skill category (empty dir — loaded from default), excludes `red-teaming/` and `self-hosting/`

### Step 7: Switch to each profile and verify

```bash
# Verify novelist
hermes profile switch novelist
hermes profile list    # Should show ◆novelist as active
hermes config get agent.reasoning_effort  # Should show: medium
hermes config get approvals.mode          # Should show: smart
ls ~/.hermes/profiles/novelist/skills/novel-os/SKILL.md  # Novel-OS skill should exist
hermes profile switch default

# Verify team-manager
hermes profile switch team-manager
hermes profile list    # Should show ◆team-manager as active
hermes config get model.default     # Should show: deepseek-v4-flash-free
hermes config get model.provider    # Should show: opencode-zen
hermes config get mcp_servers       # Should show mb14 SSH MCP server
hermes gateway status               # Should show running (or able to start)
hermes profile switch default
```

### Step 8: (Optional) Export profiles as backup tarballs

```bash
hermes profile export novelist    # Creates novelist.tar.gz
hermes profile export team-manager  # Creates team-manager.tar.gz
```

These tarballs can be imported on another machine with `hermes profile import <name>.tar.gz`.

### Step 9: Start the team-manager gateway (if needed)

```bash
hermes profile switch team-manager
hermes gateway start
```

The team-manager profile has Telegram gateway configured and is meant to run continuously. On the original setup, the gateway is `running` and connected.

## Key Config Values by Profile

### default profile (`~/.hermes/config.yaml` — 573 lines, v29)

```yaml
_config_version: 29
model:
  default: gpt-5-mini
  provider: copilot
approvals:
  mode: smart
  timeout: 60
agent:
  reasoning_effort: medium
  max_turns: 90
  service_tier: normal
  gateway_timeout: 1800
```

### novelist profile (`~/.hermes/profiles/novelist/config.yaml` — 4 lines)

```yaml
agent:
  reasoning_effort: medium
approvals:
  mode: smart
```

No explicit model — inherits fallback/global model. This is intentional: writing tasks don't need a specific model pinned.

### team-manager profile (`~/.hermes/profiles/team-manager/config.yaml` — 576 lines, v30)

```yaml
_config_version: 30
model:
  default: deepseek-v4-flash-free
  provider: opencode-zen
approvals:
  mode: smart
  timeout: 60
agent:
  reasoning_effort: medium
  max_turns: 200         # Higher than default for long delegation chains
  service_tier: fast
gateway:
  strict: false
  trust_recent_files: true
mcp_servers:
  mb14:
    command: ssh
    args:
      - asadpreuss-dodhy@192.168.1.200
      - /Users/asadpreuss-dodhy/.hermes/hermes-agent/venv/bin/hermes
      - mcp
      - serve
      - --accept-hooks
    enabled: true
kanban:
  auto_decompose: true
  dispatch_in_gateway: true
  dispatch_interval_seconds: 60
auxiliary:
  kanban_decomposer:
    timeout: 180
  mcp:
    timeout: 30
  triage_specifier:
    timeout: 120
  curator:
    timeout: 600
delegation:
  orchestrator_enabled: true
  max_concurrent_children: 3
  max_iterations: 50
  subagent_auto_approve: false
terminal:
  timeout: 180
  backend: local
toolsets:
  - hermes-cli
platform_toolsets:
  cli:
    - browser
    - delegation
    - kanban
    - memory
    - skills
    - terminal
    - web
```

## Persona Details

### default SOUL.md — Template (empty persona)

```markdown
# Hermes Agent Persona

<!--
This file defines the agent's personality and tone.
The agent will embody whatever you write here.
Edit this to customize how Hermes communicates with you.
...
-->
```

The default SOUL.md is a template with comments only — no active persona. It acts as a placeholder that can be filled with any custom persona.

### novelist SOUL.md — Warm Literary Editor

The novelist profile has a full SOUL.md that establishes:
- **Persona:** Creative writing partner and literary editor
- **Purpose:** Craft compelling fiction — novels, novellas, short stories
- **Tone:** Warm, collaborative, editorial candor (praise what works, challenge what doesn't)
- **Novel-OS aware:** Uses the 5-agent pipeline (Architect → Scribe → Editor → Guardian → Curator)
- **Craft knowledge:** Three-act structure, hero's journey, POV, voice, pacing, dialogue, subtext, theme, genre conventions

### team-manager SOUL.md — Full Team Manager (50 lines, ~3.9 KB)

The team-manager SOUL.md establishes a complete management persona:
- **Persona:** Single human-facing coordinator who organizes projects and delegates to worker agents
- **Tone:** Calm, managerial, explanatory with 2–3 sentence summaries + optional deep sections
- **Ideation:** Capture ideas with project name, priority, tags; turn into plans and tasks
- **Delegation:** Recommend agent/model/provider per task based on capability, cost, runtime
- **Verification:** Require verification artifacts (tests, lint, diffs) for all code tasks
- **Escalation:** Failed attempts escalate to stronger models via configurable policy
- **Memory policy:** Persist canonical project artifacts only; ephemeral chat requires confirmation
- **Model routing:** Small → local/small models; Medium → mid-tier; Hard/failed → frontier with approval
- **Safety:** Default approvals.mode = smart; keep secret redaction enabled

### novelist AGENTS.md — Profile Rules + Novel-OS Guide (19 lines)

The novelist profile has an AGENTS.md that:
- Declares this is the novelist profile for creative writing (isolated memory/skills)
- Stores character sheets, worldbuilding notes, plot outlines
- Sets style rules (warm, collaborative, editor-like)
- Documents Novel-OS integration (path, venv, skill, alias, 5-agent pipeline)

## Constraints

- **Config versions must match expectations** — the default profile config is v29 and team-manager is v30. Restoring a v29 config over a newer Hermes version that expects v30+ may cause some new fields to use defaults. Run `hermes update` after restoring to let Hermes upgrade configs.
- **Profile skills are separate copies** — skills are stored per-profile under `~/.hermes/profiles/<name>/skills/`. There is no symlink or deduplication. If you update a skill in one profile, the others must be updated independently.
- **Auth files are machine-specific** — the `.env` and `auth.json` files contain API keys and credentials bound to the original machine. On a new machine you must update these with valid credentials for your providers.
- **Memory and state.db are NOT in this kit** — session history, memories, and SQLite state databases are excluded. They are regenerated on first use. This is intentional: the kit restores configuration, skills, and personas, not chat history.
- **MCP server references are host-specific** — the team-manager's `mcp_servers.mb14` references a remote machine at `192.168.1.200`. On a new setup, update the host/IP and remote user to match.
- **Gateway state is not preserved** — the gateway's `running` state comes from the `gateway.pid` and `gateway.lock` files which are not restored. Start it fresh with `hermes gateway start`.

## Safety Notes

- **Do NOT commit `.env` or `auth.json` to the repo** — these files contain secrets (API keys, tokens, passwords). The `src/profiles/*/` paths in this kit are placeholders. Store actual credential files outside version control (e.g., in an encrypted vault or 1Password) and copy them manually.
- **Profile switch invalidates active sessions** — running `hermes profile switch` while in an active session will terminate the current session. Use `/reset` or start a fresh terminal.
- **Gateway credentials** — the team-manager gateway runs with the profile's auth. Ensure Telegram/Discord tokens in `auth.json` are valid before starting the gateway.
- **Permissions** — all `.env` and `auth.json` files should be `chmod 600` to prevent other processes from reading them.
- **Novel-OS path is hardcoded** — the novelist AGENTS.md references `/Users/dodhya/novel-os/`. On a new machine, adjust this path or clone Novel-OS to match.
- **If a profile refuses to switch** — `hermes profile create <name>` must be run before `hermes profile switch`. The profile must exist in the internal registry before Hermes can activate its directory.

## Failures Overcome

1. **Missing profile directories** — `hermes profile create` creates the registry entry but may not create all subdirectories. The `mkdir -p` in Step 2 ensures `skills/`, `cron/`, `hooks/`, `logs/`, `cache/`, and `memories/` exist before any file copies.
2. **Team-manager profile directory structure is richer** — novelist needs only 7 subdirectories while team-manager needs 16+ (plugins, sessions, state-snapshots, bin, lsp, plans, sandboxes, skins, workspace). A blanket `cp -a` from one profile to another will miss these.
3. **Skill category differences between profiles** — not all skills are present in all profiles. `red-teaming/` and `self-hosting/` exist only in default. `novel-os/` exists only in novelist. `writing-tools-evaluation/` is novelist-specific. Always restore per-profile, not by copying the default profile's skills everywhere.
4. **hermes-agent skill is empty in team-manager** — the `~/.hermes/profiles/team-manager/skills/hermes-agent/` directory exists but has 0 skills. The actual hermes-agent skill lives in the default profile and is shared at runtime. Do not overwrite with a stale copy.
5. **Config version mismatch** — restoring across Hermes versions can cause field rejection. Always run `hermes update` after restoring configs to let Hermes upgrade them to the current version.
6. **Gateway lock file** — if a previous gateway didn't shut down cleanly, `gateway.lock` may exist and block a new gateway start. Remove it with `rm -f ~/.hermes/profiles/team-manager/gateway.lock`.

## Validation

After completing all steps, this checklist confirms success:

### Default profile

- [ ] `hermes profile list` shows `default` with model `gpt-5-mini`
- [ ] `~/.hermes/config.yaml` exists (573 lines, v29)
- [ ] `~/.hermes/SOUL.md` exists with the template comment
- [ ] `~/.hermes/skills/` has 21 category directories
- [ ] Skills are loadable — e.g., `hermes -s software-development`
- [ ] `~/.hermes/.env` and `~/.hermes/auth.json` exist and are chmod 600

### Novelist profile

- [ ] `hermes profile list` shows `novelist` with no explicit model
- [ ] `hermes profile switch novelist` succeeds
- [ ] `~/.hermes/profiles/novelist/config.yaml` exists (4 lines)
- [ ] `~/.hermes/profiles/novelist/SOUL.md` contains the literary editor persona
- [ ] `~/.hermes/profiles/novelist/AGENTS.md` contains Novel-OS integration guide
- [ ] `~/.hermes/profiles/novelist/skills/novel-os/SKILL.md` exists
- [ ] `~/.hermes/profiles/novelist/skills/writing/writing-tools-evaluation/SKILL.md` exists
- [ ] Profile `.env` and `auth.json` exist and are chmod 600

### Team-manager profile

- [ ] `hermes profile list` shows `team-manager` with model `deepseek-v4-flash-free`
- [ ] `hermes profile switch team-manager` succeeds
- [ ] `~/.hermes/profiles/team-manager/config.yaml` exists (576 lines, v30)
- [ ] `~/.hermes/profiles/team-manager/SOUL.md` exists (50-line manager persona)
- [ ] `~/.hermes/profiles/team-manager/skills/mlops/` has 6 sub-skills
- [ ] `~/.hermes/profiles/team-manager/skills/hermes-agent/` directory exists (can be empty)
- [ ] `hermes config get model.default` returns `deepseek-v4-flash-free`
- [ ] `hermes config get model.provider` returns `opencode-zen`
- [ ] `hermes config get mcp_servers` shows the `mb14` SSH MCP server entry
- [ ] `hermes gateway start` succeeds (if credentials are valid)
- [ ] Profile `.env` and `auth.json` exist and are chmod 600
- [ ] Profile has `plugins/`, `sessions/`, `state-snapshots/`, `bin/`, `lsp/`, `plans/`, `sandboxes/`, `skins/`, `workspace/` directories

### Overall

- [ ] Switching between all 3 profiles works: `hermes profile switch default` → `switch novelist` → `switch team-manager`
- [ ] No permission errors on any profile file
- [ ] Each profile loads skills on `/skill` command in session
- [ ] Config values match expectations per profile
