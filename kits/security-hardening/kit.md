---
name: security-hardening-suite
description: "Lock down a Hermes Agent with Tirith custom rules, smart approvals mode, and a comprehensive secure-credentials skill."
version: 1.0.0
author: dodhya
models:
  primary: gpt-5-mini via copilot
  required_models: []
services:
  tirith:
    required: true
    description: "Auto-installed on first terminal() use in Hermes. Scans every command for credential leakage, pipe-to-shell, and dangerous patterns."
    setup: "Auto — no manual install needed. Run `~/.hermes/bin/tirith policy validate` to verify."
parameters:
  approvals.mode: smart
  approvals.timeout: 60
environment:
  os: [macos]
  homebrew: false
  hermes_version: ">=0.1.0"
src:
  fileManifest:
    - path: src/.tirith/policy.yaml
      role: "Tirith policy — custom rules for inline SSH password, curl -u basic auth, and inline env credential blocking"
      destination: ~/.tirith/policy.yaml
    - path: src/secure-credentials/SKILL.md
      role: "Hermes skill — security-first operations covering credentials, secrets, network, data safety, system config, and git"
      destination: ~/.hermes/skills/software-development/secure-credentials/SKILL.md
---

## Goal

Prevent credential leakage, enforce security best practices, and lock down all agent operations. Every terminal command is scanned at runtime — inline passwords, tokens, and API keys are blocked before they reach the shell.

## When to Use

- **Every new Hermes install** — run this kit after basic setup, before connecting any services
- **After a security review** — verify Tirith rules are active and the skill is loaded
- **When migrating to a new machine** — apply the same policy on the new host
- **Anytime credentials appear in agent output** — the regex rules catch what the agent misses

## Setup

### What you need

- Hermes Agent running (any profile)
- Terminal access (commands run via Hermes terminal tool)
- No prior `~/.tirith/policy.yaml` (existing one will be overwritten)

### What this kit installs

| File | Destination | Purpose |
|------|-------------|---------|
| `src/.tirith/policy.yaml` | `~/.tirith/policy.yaml` | Custom Tirith rules: sshpass `-p` → BLOCK, `curl -u` → BLOCK, inline env creds → WARN |
| `src/secure-credentials/SKILL.md` | `~/.hermes/skills/software-development/secure-credentials/SKILL.md` | Hermes skill: 6-domain security reference the agent follows on every command |

## Steps

### Step 1: Install the Tirith policy

Copy the custom rules into place:

```bash
mkdir -p ~/.tirith
cp src/.tirith/policy.yaml ~/.tirith/policy.yaml
chmod 644 ~/.tirith/policy.yaml
```

Verify the policy is valid:

```bash
~/.hermes/bin/tirith policy validate
```

Expected output:

```
✓ policy.yaml — valid
```

If `tirith` isn't installed yet, it auto-downloads on the first `terminal()` call in Hermes. Run the validate command again after a terminal call.

### Step 2: Test the rules work

```bash
# This should be BLOCKED:
~/.hermes/bin/tirith check "sshpass -p secret123 ssh user@host"

# This should be ALLOWED:
~/.hermes/bin/tirith check "ssh user@host ls"
```

The blocked command returns exit code 1 with a message about the custom rule. The allowed command passes through.

### Step 3: Enable smart approvals

Set your Hermes config to use AI-assisted approval scanning:

```bash
hermes config set approvals.mode smart
hermes config set approvals.timeout 60
```

This activates the auxiliary LLM that catches anything the Tirith regex misses. After setting, start a new session (`/reset` or new `hermes` invocation) for the change to take effect.

### Step 4: Install the secure-credentials skill

```bash
mkdir -p ~/.hermes/skills/software-development/secure-credentials
cp src/secure-credentials/SKILL.md ~/.hermes/skills/software-development/secure-credentials/SKILL.md
```

To verify it loads:

```bash
# In a Hermes session:
/skill secure-credentials
```

Or on startup:

```bash
hermes -s secure-credentials
```

### Step 5: Verify everything is active

```bash
# 1. Tirith functional
~/.hermes/bin/tirith check "sshpass -p test ssh host" && echo "BLOCK FAILED" || echo "BLOCK OK"

# 2. Config set
hermes config get approvals.mode
# Should show: smart

# 3. Skill installed
ls ~/.hermes/skills/software-development/secure-credentials/SKILL.md
```

## Constraints

- **Tirith only scans terminal commands**, not HTTP calls, file writes, or code execution paths
- **Smart approvals** need an auxiliary LLM configured — without one, it falls back to the built-in DANGEROUS_PATTERNS detector
- **`fail_mode: open`** in the policy means scanning errors are treated as allow — the policy won't cause false positives from broken regex
- **`allow_bypass_env: true`** allows `TIRITH=0` bypass in interactive terminals — this is intentional for debugging; disable it for stricter enforcement
- The policy catches inline credential *patterns* but not all credential *shapes* — a carefully obfuscated secret on the command line could still slip through
- Profile isolation: the skill must be copied to each Hermes profile's `skills/` directory if you want it available in multiple profiles

## Safety Notes

- Tirith can block legitimate commands that happen to match the regex (e.g., a file named `sshpass-data` in a command). Use the allowlist if needed.
- Setting `approvals.mode: off` disables all approval prompts — only do this on isolated/dev machines
- The `--accept-hooks` flag on gateway auto-approves shell operations — understand the risk if running the API server gateway
- If you need to temporarily bypass Tirith for a command, prefix with `TIRITH=0 ` — but never use this for credential-bearing commands

## Failures Overcome

1. **Tilde expansion in `tailscaled` arguments** — `--state=~/.hermes/file` doesn't expand because the `=` prevents shell expansion. Use full absolute paths.
2. **Tirith auto-download** — doesn't install until the first terminal command in a session. Run a harmless command first (`echo ok`) if `tirith policy validate` fails.
3. **Config changes need session restart** — `hermes config set approvals.mode smart` doesn't take effect until the next Hermes session. Use `/reset` or start a new `hermes` invocation.

## Validation

After completing all steps, this checklist confirms success:

- [ ] `~/.tirith/policy.yaml` exists and is valid (`tirith policy validate`)
- [ ] `sshpass -p` commands are BLOCKED at runtime
- [ ] `curl -u user:password` commands are BLOCKED at runtime
- [ ] Inline `PASSWORD=***` env vars are WARNED
- [ ] `approvals.mode` is `smart`
- [ ] `secure-credentials` skill is loadable (`/skill secure-credentials`)
