---
name: model-providers
description: "Document and restore all Hermes model provider configurations — Copilot (GitHub OAuth, device code flow) and OpenCode Zen (API key). Includes per-profile auth setup, credential pool recovery, and verification steps."
version: 1.0.0
author: dodhya
models:
  primary: gpt-5-mini via copilot / deepseek-v4-flash-free via opencode-zen
  required_models:
    - gpt-5-mini
    - deepseek-v4-flash-free
services:
  github-copilot:
    required: true
    description: "Default profile model provider. Uses GitHub Copilot API at api.githubcopilot.com. Auth via device code flow (NOT gh auth login). Tokens are gho_* format, not github_pat_*."
    setup: "Run `hermes model` select GitHub Copilot → device code flow"
  opencode-zen:
    required: true
    description: "Team-manager and novelist profile model provider. Connects to https://opencode.ai/zen/v1 with an API key stored in profile .env as OPENCODE_ZEN_API_KEY."
    setup: "Set OPENCODE_ZEN_API_KEY in profile .env, then `hermes auth add opencode-zen`"
parameters:
  model.default: gpt-5-mini (default profile), deepseek-v4-flash-free (team-manager profile)
  model.provider: copilot (default), opencode-zen (team-manager, novelist)
environment:
  os: [macos]
  homebrew: false
  hermes_version: ">=0.1.0"
profiles:
  default: ~/.hermes/config.yaml
  team-manager: ~/.hermes/profiles/team-manager/config.yaml
  novelist: ~/.hermes/profiles/novelist/config.yaml
---

## Goal

Document all model provider configurations used across Hermes profiles, provide step-by-step restoration instructions for each provider from scratch, and explain the auth model (credential pool, per-profile isolation, token formats). After following this kit, any profile should be able to authenticate and use its designated model provider.

## When to Use

- **On a fresh Hermes install** — after the base setup wizard, run this kit to attach the model providers
- **After auth expiry / token revocation** — Copilot OAuth tokens (gho_*) can expire; re-auth is needed
- **When migrating profiles to a new machine** — reconstruct the same provider setup on the new host
- **When credential-pool corruption occurs** — remove stale entries and re-add credentials
- **When switching the primary model** — know how to change model/provider per profile

## Provider Overview

| Provider | Auth Method | Token Format | Profiles Using It | Default Model |
|----------|------------|--------------|-------------------|---------------|
| **Copilot** (GitHub Copilot) | Device code flow via `hermes model` | `gho_*` (GitHub Copilot OAuth token) | default | `gpt-5-mini` |
| **OpenCode Zen** | API key in profile `.env` | `OPENCODE_ZEN_API_KEY` env var | team-manager, novelist | `deepseek-v4-flash-free` |

### How Auth Works in Hermes

Hermes uses a **credential pool** stored per-profile in `auth.json`. Each provider has one or more credential entries with metadata (source, priority, base_url, last_status). The pool is checked at runtime; if an entry's `last_status` is `ok` the provider is considered logged in.

Auth state is **per-profile** — each profile's `auth.json` is independent. The default profile's auth lives at `~/.hermes/auth.json`, while named profiles store theirs at `~/.hermes/profiles/<name>/auth.json`.

### Key Distinctions

- **Copilot OAuth (`gho_*` tokens) ≠ `gh auth login` (`github_pat_*` tokens)**. The GitHub CLI's `gh auth login` produces a personal access token; Copilot uses a separate device-code OAuth flow that issues a `gho_*` token scoped to api.githubcopilot.com. Do NOT confuse the two.
- The credential pool can contain both `gh_cli`-sourced tokens and env-sourced tokens simultaneously. Hermes picks by priority (lower number = higher priority).
- **OpenCode Zen** requires no external binary — just the API key in the environment and the `opencode-zen` provider configured in the profile's `model` section.

## What This Kit Covers

| Topic | Description |
|-------|-------------|
| Per-profile model configurations | What's set in each profile's config.yaml |
| Auth file locations | Where auth.json, .env, and auth.lock live per profile |
| Provider restoration | Step-by-step: Copilot (device code flow), OpenCode Zen (API key) |
| Token troubleshooting | Expired tokens, wrong token type, credential pool conflicts |
| Verification | How to confirm each provider is logged in and working |

## Current Configuration

### Default Profile (`~/.hermes/config.yaml`)

```yaml
model:
  api_mode: chat_completions
  base_url: ''
  default: gpt-5-mini
  provider: copilot
```

- **Auth file**: `~/.hermes/auth.json`
- **Secrets file**: `~/.hermes/.env` (largely a template — Copilot doesn't need a key in .env)
- **Auth type**: `gho_*` GitHub Copilot OAuth token (device code flow)
- **Credential source**: `env:COPILOT_GITHUB_TOKEN` (fallback) or device-code flow token

### Team-Manager Profile (`~/.hermes/profiles/team-manager/config.yaml`)

```yaml
model:
  default: deepseek-v4-flash-free
  provider: opencode-zen
```

- **Auth file**: `~/.hermes/profiles/team-manager/auth.json`
- **Secrets file**: `~/.hermes/profiles/team-manager/.env`
- **Auth type**: API key (`OPENCODE_ZEN_API_KEY`) stored in `.env`
- **API base URL**: `https://opencode.ai/zen/v1`
- **Model**: deepseek-v4-flash-free (free-tier model via OpenCode Zen)

### Novelist Profile (`~/.hermes/profiles/novelist/config.yaml`)

```yaml
agent:
  reasoning_effort: low
approvals:
  mode: smart
```

- **No explicit model** — inherits fallback from the Hermes default
- **Auth file**: `~/.hermes/profiles/novelist/auth.json`
- **Secrets file**: `~/.hermes/profiles/novelist/.env` (template, no keys set)
- **Credential pool**: Contains `opencode-zen` entry (same API key env ref as team-manager)

## Setup

### What you need

- Hermes Agent installed and running
- Terminal access (commands run via Hermes terminal tool)
- A GitHub account with Copilot access (for Copilot provider)
- An OpenCode Zen API key (for opencode-zen provider)

### Files involved

| File | Purpose |
|------|---------|
| `~/.hermes/auth.json` | Default profile credential pool — Copilot token storage |
| `~/.hermes/.env` | Default profile environment (mostly a template) |
| `~/.hermes/profiles/team-manager/auth.json` | Team-manager credential pool — Copilot + OpenCode Zen |
| `~/.hermes/profiles/team-manager/.env` | Team-manager secrets — OPENCODE_ZEN_API_KEY, Telegram tokens |
| `~/.hermes/profiles/novelist/auth.json` | Novelist credential pool — OpenCode Zen |
| `~/.hermes/profiles/novelist/.env` | Novelist environment (template, largely empty) |

## Steps

### Step 1: Verify current auth state

Check what providers are configured and logged in:

```bash
hermes auth list
```

Expected output when all providers are healthy:

```
copilot (1 credentials):
  #1  gh auth token        api_key gh_cli ←

opencode-zen (1 credentials):
  #1  OPENCODE_ZEN_API_KEY api_key env:OPENCODE_ZEN_API_KEY ←
```

The `←` marker indicates the active/selected credential. Check individual provider status:

```bash
hermes auth status copilot
hermes auth status opencode-zen
```

Expected: `copilot: logged in` and `opencode-zen: logged in`.

### Step 2: Restore Copilot provider (default profile)

Copilot uses a **device code OAuth flow**. This is NOT the same as `gh auth login`.

> **Important**: The token produced is a `gho_*` token (GitHub Copilot OAuth), NOT a `github_pat_*` personal access token. If you accidentally use a PAT, Hermes will reject it.

#### Option A: Fresh setup via `hermes model`

```bash
# Run the model setup wizard (interactive)
hermes model
```

In the interactive menu:
1. Select **GitHub Copilot** as the provider
2. Select **device code flow** as the auth method
3. Follow the on-screen instructions:
   - A device code URL will be displayed (e.g., `https://github.com/login/device`)
   - A user code (e.g., `ABCD-1234`) will be shown
   - Open the URL in a browser, enter the code, and authorize
4. Once authorized, the token is stored in `~/.hermes/auth.json` automatically

#### Option B: Re-auth after token expiry

If Copilot auth has expired or is failing, remove the stale credential first:

```bash
# Remove the old Copilot credential (use the correct ID from hermes auth list)
hermes auth remove copilot

# Now re-run the device code flow
hermes model
```

Select **GitHub Copilot** → **device code flow** as above.

#### Option C: Manual credential pool edit (advanced)

If `hermes auth remove` doesn't work, you can manually edit `auth.json`:

```bash
# Remove the copilot entry from credential_pool in ~/.hermes/auth.json
# Then run hermes model to re-auth
```

**Do not manually craft a token entry** — always use the device code flow to get a valid gho_* token.

#### What NOT to do

```bash
# ❌ NOT THIS — produces a github_pat_*, not a gho_* Copilot token
gh auth login

# ❌ NOT THIS — Copilot does not accept OpenRouter or OpenAI keys
hermes auth add copilot --type api_key --key sk-...
```

### Step 3: Restore OpenCode Zen provider (team-manager / novelist)

OpenCode Zen uses standard API-key auth. The key is stored in the profile's `.env` file.

#### Step 3a: Obtain an OpenCode Zen API key

1. Visit [https://opencode.ai](https://opencode.ai) and sign up / log in
2. Navigate to the API keys section
3. Create a new API key

#### Step 3b: Set the API key in the profile's .env

For the **team-manager** profile:

```bash
echo 'OPENCODE_ZEN_API_KEY=your_key_here' >> ~/.hermes/profiles/team-manager/.env
chmod 600 ~/.hermes/profiles/team-manager/.env
```

For the **novelist** profile (if needed):

```bash
echo 'OPENCODE_ZEN_API_KEY=your_key_here' >> ~/.hermes/profiles/novelist/.env
chmod 600 ~/.hermes/profiles/novelist/.env
```

#### Step 3c: Add credential to the pool

```bash
# Add the opencode-zen credential from the env var
hermes auth add opencode-zen
```

This reads `OPENCODE_ZEN_API_KEY` from the profile's `.env` and registers it in `auth.json`.

#### Step 3d: Ensure the profile config has the provider set

Check the profile's `model` section. For team-manager:

```bash
# Verify in ~/.hermes/profiles/team-manager/config.yaml
model:
  default: deepseek-v4-flash-free
  provider: opencode-zen
```

If missing, set it:

```bash
hermes config set model.default deepseek-v4-flash-free
hermes config set model.provider opencode-zen
```

For the novelist profile, there's currently no explicit model set — it inherits the Hermes default. If you want to add one:

```bash
# Switch to novelist profile first
# Then:
hermes config set model.default deepseek-v4-flash-free
hermes config set model.provider opencode-zen
```

### Step 4: Configure a specific profile's model provider

Profiles isolate both config and auth. To switch which profile you're configuring:

```bash
# Check current active profile
cat ~/.hermes/active_profile

# Switch profiles (from within the Hermes CLI)
# Or set the profile on startup:
hermes --profile team-manager
```

Once in the right profile context:

```bash
# Set model provider
hermes config set model.provider copilot      # for GitHub Copilot
hermes config set model.provider opencode-zen  # for OpenCode Zen

# Set the default model
hermes config set model.default gpt-5-mini
hermes config set model.default deepseek-v4-flash-free
```

### Step 5: Verify everything is active

```bash
# 1. List all configured providers and their credentials
hermes auth list

# 2. Check each provider's login status
hermes auth status copilot
hermes auth status opencode-zen

# 3. Verify model configuration per profile
# Default profile:
cat ~/.hermes/config.yaml | grep -A5 "^model:"

# Team-manager profile:
cat ~/.hermes/profiles/team-manager/config.yaml | grep -A5 "model:"

# 4. Check auth file integrity (should be valid JSON)
python3 -c "import json; json.load(open('$HOME/.hermes/auth.json'))" && echo "default auth OK"
python3 -c "import json; json.load(open('$HOME/.hermes/profiles/team-manager/auth.json'))" && echo "team-manager auth OK"
python3 -c "import json; json.load(open('$HOME/.hermes/profiles/novelist/auth.json'))" && echo "novelist auth OK"

# 5. Test with a model query (if Hermes is running)
hermes -m "Hello — respond with just the word OK" 2>&1 | tail -5
```

## File Inventory

For backup and recovery purposes, these are the key files:

### Auth state files

| Profile | Auth File | Secrets File |
|---------|-----------|-------------|
| default | `~/.hermes/auth.json` (1.3KB) | `~/.hermes/.env` (template, not used for Copilot) |
| team-manager | `~/.hermes/profiles/team-manager/auth.json` (1.2KB) | `~/.hermes/profiles/team-manager/.env` (436B) |
| novelist | `~/.hermes/profiles/novelist/auth.json` (664B) | `~/.hermes/profiles/novelist/.env` (template, ~23KB) |

### Lock files

| File | Purpose |
|------|---------|
| `~/.hermes/auth.lock` | Prevents concurrent auth operations (default profile) |
| `~/.hermes/profiles/team-manager/auth.lock` | Lock for team-manager profile auth |

## Constraints

- **Copilot device code flow is interactive** — it requires a browser. Cannot be fully automated in a headless setup. You must open the GitHub URL and enter the code.
- **`hermes model` requires an interactive terminal** — it cannot be run through a pipe or non-interactive subprocess (`hermes auth` commands work non-interactively).
- **Profile isolation** — each profile has its own `auth.json` and `.env`. Adding a credential to one profile does NOT make it available in another.
- **OPENCODE_ZEN_API_KEY must be set before adding the credential** — `hermes auth add opencode-zen` reads the env var at the time of the command. If the `.env` file was just edited, ensure the current shell has sourced it.
- **Lock files** — `auth.lock` files indicate concurrent auth operations. If auth commands fail, check if a stale lock file exists and remove it.
- **Novelist profile has no explicit model** — if the Hermes default provider or model changes, novelist inherits the new default. To pin it, set model config explicitly.

## Safety Notes

- **Never commit `.env` files or `auth.json` to version control** — they contain API keys and OAuth tokens.
- **Copilot `gho_*` tokens have no expiry listed in the credential pool** — they can expire silently. If Copilot starts failing, re-run the device code flow.
- **Do not mix credential sources** — if you have both a `gh_cli`-sourced token and an `env:`-sourced token for the same provider, Hermes picks by priority. Remove the one you don't want.
- **Profile .env files are mode 600** — if you create or edit one, set permissions: `chmod 600 <path-to-.env>`.

## Failures Overcome

1. **`hermes model` refuses to run non-interactively** — it requires a real terminal with PTY. Use `hermes auth add/provider` commands instead for scripting/automation.
2. **`gh auth login` produces the wrong token type** — the GitHub CLI issues `github_pat_*` tokens, not `gho_*` Copilot tokens. Always use `hermes model` → device code flow.
3. **OpenCode Zen binary not needed** — the task context mentioned `/opt/homebrew/bin/opencode` but the Hermes `opencode-zen` provider connects directly via API key to `https://opencode.ai/zen/v1`. No local binary is required.
4. **Profile `.env` templates are large (~23KB)** — for novelist and default profiles the `.env` is a full Hermes template with all keys commented out. Only the actual key lines matter.
5. **Lock files can become stale** — if an auth command is interrupted, `auth.lock` may persist. Remove it manually: `rm ~/.hermes/profiles/<name>/auth.lock`.

## Validation

After completing all steps, this checklist confirms success:

- [ ] `hermes auth list` shows both `copilot` and/or `opencode-zen` providers
- [ ] `hermes auth status copilot` returns `copilot: logged in` (if Copilot is used)
- [ ] `hermes auth status opencode-zen` returns `opcode-zen: logged in` (if OpenCode Zen is used)
- [ ] Default profile config has `model.provider: copilot` and `model.default: gpt-5-mini`
- [ ] Team-manager profile config has `model.provider: opencode-zen` and `model.default: deepseek-v4-flash-free`
- [ ] Each `auth.json` is valid JSON (no parse errors)
- [ ] Each `.env` file has permissions `600` and contains the correct keys
- [ ] A test model query returns successfully: `hermes -m "ping"` (in each profile)
