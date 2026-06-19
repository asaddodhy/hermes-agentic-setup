---
name: profile-oauth-setup
description: "Full OAuth credential setup for a Hermes profile — Google services (Drive, Gmail, Calendar) via OAuth 2.0 desktop flow, and GitHub Copilot via OAuth device code flow. Covers read-only and read-write access, macOS keychain nuances, and verification."
version: 1.0.0
author: dodhya
models:
  primary: any
services:
  google-cloud:
    required: false
    description: "Google Cloud project with OAuth 2.0 Client ID (Desktop app type). Needed only for Google services (Drive, Gmail, Calendar)."
    setup: "Visit https://console.cloud.google.com/apis/credentials → Create Credentials → OAuth client ID → Desktop application → Download JSON"
  gh:
    required: false
    description: "GitHub CLI — needed only for Copilot auth to resolve a `gho_*` token via device code flow."
    setup: "brew install gh"
parameters:
  google.scope.readonly: "https://www.googleapis.com/auth/drive.readonly, https://www.googleapis.com/auth/documents.readonly"
  google.scope.readwrite: "https://www.googleapis.com/auth/drive, https://www.googleapis.com/auth/documents"
  copilot.token_env_var: COPILOT_GITHUB_TOKEN
  copilot.storage: ~/.hermes/.env
  google.credential_path: "~/.hermes/profiles/<profile-name>/google_client_secret.json"
  google.token_path: "~/.hermes/profiles/<profile-name>/google_token.json"
environment:
  os: [macos, linux, windows]
  hermes_version: ">=0.1.0"
dependencies:
  google:
    - google-workspace skill (for the setup.py script)
    - pip packages: google-auth-oauthlib, google-auth-httplib2, google-api-python-client
  copilot:
    - gh CLI (for device code flow fallback)
    - Alternatively: Python from the Hermes venv (no extra installs needed)
security:
  secrets_stored:
    - name: Google OAuth client secret
      location: "~/.hermes/profiles/<profile>/google_client_secret.json"
      sensitive: true
      note: "Desktop app client secret — treat as confidential"
    - name: Google OAuth token
      location: "~/.hermes/profiles/<profile>/google_token.json"
      sensitive: true
      note: "Contains refresh token — if compromised, revoke at https://myaccount.google.com/permissions"
    - name: Copilot GitHub token
      location: "~/.hermes/.env (COPILOT_GITHUB_TOKEN)"
      sensitive: true
      note: "gho_* OAuth token — provides Copilot API access"
  known_limits:
    - "Google OAuth auth codes expire in minutes — generate fresh URL if user doesn't complete quickly"
    - "Google OAuth tokens can be revoked by the user at any time via myaccount.google.com/permissions"
    - "Copilot gho_* tokens are tied to the Copilot subscription — if the subscription lapses, the token becomes invalid"
tags: [oauth, auth, credentials, google, copilot, profile, setup, integration]
---

# Profile OAuth Setup Kit

## Goal

Set up OAuth credentials for external services scoped to a **specific Hermes profile**, giving the agent access to:

- **Google services** (Drive, Gmail, Calendar) — read-only or read-write
- **GitHub Copilot** as an LLM provider — via `gho_*` OAuth token

Credentials are stored per-profile, keeping access isolated between Hermes profiles.

---

## When to Use

- **Fresh installation**: Setting up a new Mac or new Hermes profile from scratch
- **Adding a new profile**: E.g. creating a `novelist` profile that needs Google Drive access
- **Recovering from credential loss**: Token expired, revoked, or secret file lost
- **Restoring after system wipe**: After a clean OS install
- **Switching access levels**: Upgrading from read-only to read-write Google access
- **Setting up a new Copilot account**: Got a new Copilot subscription on a different GitHub account

---

## Setup

### Prerequisites

| Requirement | Check | Needed for |
|-------------|-------|------------|
| Hermes Agent installed and running | `hermes status` | Both |
| Google Cloud project with OAuth client | See Step 1 below | Google only |
| gh CLI installed (optional) | `gh --version` | Copilot only |
| Target Hermes profile exists | `hermes profile list` or check `~/.hermes/profiles/` | Both |

### What this kit configures

| Component | Location | Purpose |
|-----------|----------|---------|
| Google client secret | `~/.hermes/profiles/<profile>/google_client_secret.json` | OAuth client credentials |
| Google token | `~/.hermes/profiles/<profile>/google_token.json` | OAuth 2.0 access + refresh token |
| Google Pending OAuth state | `~/.hermes/profiles/<profile>/google_oauth_pending.json` | PKCE state for auth URL exchange |
| Copilot GitHub token | `~/.hermes/.env` (`COPILOT_GITHUB_TOKEN=gho_...`) | API access for Copilot LLM provider |

---

## Part A — Google OAuth Setup

### Step A1 — Create a Google Cloud project (first time only)

If you don't have a project yet:

1. Go to https://console.cloud.google.com/projectcreate
2. Name it (e.g. "Hermes Agent Access")
3. Note the **Project ID** — you'll need it

### Step A2 — Enable required APIs

Enable the APIs your profile needs:

- **Google Drive API** — https://console.cloud.google.com/apis/library/drive.googleapis.com
- **Google Docs API** — https://console.cloud.google.com/apis/library/docs.googleapis.com
- **Gmail API** (if needed) — https://console.cloud.google.com/apis/library/gmail.googleapis.com
- **Google Calendar API** (if needed) — https://console.cloud.google.com/apis/library/calendar-json.googleapis.com

Click **Enable** for each.

### Step A3 — Create OAuth 2.0 Client ID

1. Go to https://console.cloud.google.com/apis/credentials
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: "Hermes Profile — <profile-name>"
5. Click **Create**
6. Click **Download JSON** → save the file (e.g. `client_secret_XXXX.json`)

### Step A4 — Choose access level

**Read-only** (safe — agent can view/download, cannot create/edit/delete):
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]
```

**Read-write** (full access — agent can create, edit, upload, delete):
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]
```

**For Gmail or Calendar**, add:
- `https://www.googleapis.com/auth/gmail.readonly` or `https://mail.google.com/`
- `https://www.googleapis.com/auth/calendar.readonly` or `https://www.googleapis.com/auth/calendar`

### Step A5 — Run OAuth setup

The kit relies on the `google-workspace` skill's `setup.py` script. Load the skill first:

```bash
skill_view(name='google-workspace')
```

Set up the shorthand:

```bash
GSETUP="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/setup.py"
```

Check if already set up:

```bash
$GSETUP --check
```

If it prints `AUTHENTICATED`, Google OAuth is already configured for this profile.

### Step A6 — Store client secret

```bash
$GSETUP --client-secret /path/to/client_secret_XXXX.json
```

This copies the secret to `~/.hermes/profiles/<profile-name>/google_client_secret.json`.

### Step A7 — Update scopes for read-write

If choosing **read-write**, patch the `SCOPES` list in `setup.py` (lines 46-49) before generating the auth URL:

```bash
# Edit ~/.hermes/skills/productivity/google-workspace/scripts/setup.py
# Change:
# SCOPES = [
#     "https://www.googleapis.com/auth/drive.readonly",
#     "https://www.googleapis.com/auth/documents.readonly",
# ]
# To:
# SCOPES = [
#     "https://www.googleapis.com/auth/drive",
#     "https://www.googleapis.com/auth/documents",
# ]
```

Then revoke any existing token first:

```bash
$GSETUP --revoke
```

### Step A8 — Generate authorization URL

```bash
$GSETUP --auth-url
```

This prints a URL. Send it to the person authorizing:

1. Open the URL in a browser
2. Sign in with the Google account to authorize
3. Review the scopes (un-check any not needed)
4. Click **Allow**
5. Browser redirects to `http://localhost:1/?code=...` — page may fail to load, that's expected
6. **Copy the entire redirected URL** from the address bar

### Step A9 — Handle "403: access_denied" (testing mode)

If the user gets `Error 403: access_denied`, the Google Cloud project is in **Testing** mode and the user's email isn't a test user.

**Fix:** Go to https://console.cloud.google.com/auth/audience → **Audience** → **Test users** → **Add users** → enter their email → **Save**.

Generate a **fresh** auth URL after adding them — the old one won't work.

### Step A10 — Exchange auth code for token

```bash
$GSETUP --auth-code "http://localhost:1/?code=4/0A...&scope=..."
```

Paste the full redirect URL or just the `code=...` value — the script handles both.

### Step A11 — Verify Google authentication

```bash
$GSETUP --check
```

Expected output: `AUTHENTICATED: Token valid at ~/.hermes/profiles/<profile-name>/google_token.json`

For a live API test with stricter validation:

```bash
$GSETUP --check-live
```

---

## Part B — GitHub Copilot Auth Setup

### Step B1 — Prerequisites

You need a GitHub account **with an active Copilot subscription**. This may be a different account from your git/gh operations account — that's fine.

**macOS caveat:** On macOS, `gh` stores authentication tokens in the system Keychain Access, NOT in `~/.config/gh/`. Moving or deleting `~/.config/gh` does NOT stop `gh auth token` from returning a valid token. The solution isn't to hide the `gh` token, but to set `COPILOT_GITHUB_TOKEN` in `.env` — the env var takes priority.

### Step B2 — Remove stale tokens

```bash
# Clear any existing token from .env
sed -i '' '/^COPILOT_GITHUB_TOKEN/d' ~/.hermes/.env

# Clear stored copilot credentials in Hermes
hermes auth remove copilot 1

# Unset the env var if still set in current shell
unset COPILOT_GITHUB_TOKEN
```

### Step B3 — Trigger the OAuth device code flow

**Option A — Direct Python call** (most reliable):

```bash
cd ~/.hermes/hermes-agent
source .venv/bin/activate 2>/dev/null || source venv/bin/activate 2>/dev/null
python3 -c "
from hermes_cli.copilot_auth import copilot_device_code_login
token = copilot_device_code_login()
if token:
    print('SUCCESS=' + token)
else:
    print('FAILED')
"
```

**Option B — Via `hermes model`** (works when no token is detected):

```bash
unset COPILOT_GITHUB_TOKEN
hermes model
```

Pick **GitHub Copilot**, then **Option 1: Login with GitHub (OAuth device code flow)**.

### Step B4 — Authorize in the browser

1. Open **https://github.com/login/device** in a browser
2. **Sign out of any logged-in accounts** (or use a private/incognito window)
3. Sign in with your **Copilot-enabled account** (NOT the git/gh operations account)
4. Enter the device code shown in the terminal
5. Click **Authorize**

### Step B5 — Save the token

After the command prints `SUCCESS=gho_...`, save it to `~/.hermes/.env`:

```bash
echo 'COPILOT_GITHUB_TOKEN=gho_...' >> ~/.hermes/.env
```

Replace `gho_...` with the full token. This env var takes priority over `gh auth token` in the resolve chain.

**Important:** Use `write_file` with the complete file content to avoid shell redirection issues in the agent's approval flow. Never use `echo >>` in an agent session — it can silently lose content.

### Step B6 — Restore `gh` config (if you moved it)

```bash
mv ~/.config/gh.bak ~/.config/gh 2>/dev/null; true
```

### Step B7 — Verify Copilot setup

```bash
hermes model
```

You should see the Copilot model list. Pick a model to set it as default. Then test:

```bash
hermes -m gpt-5.5
```

---

## Part C — Combined verification

```text
[ ] Google token exists:   ls ~/.hermes/profiles/<profile>/google_token.json
[ ] Google is AUTHENTICATED: $GSETUP --check → "AUTHENTICATED"
[ ] Google live API works: $GSETUP --check-live
[ ] Copilot token set:     grep "COPILOT_GITHUB_TOKEN" ~/.hermes/.env
[ ] Copilot model list:    hermes model (shows Copilot models)
[ ] Profile isolation:     Each profile has its own Google token in ~/.hermes/profiles/<profile>/
```

---

## Constraints

- **Google OAuth codes expire in minutes** — generate the auth URL and send it to the user immediately. If they don't complete the flow quickly, generate a fresh URL.
- **Profile isolation** — Google credentials for Profile A do NOT give Profile B access. Each profile needs its own OAuth setup.
- **Read-only vs read-write is hard to change** — switching requires `--revoke` first, then re-auth. Google won't issue a token with fewer scopes without revocation.
- **macOS keychain persists `gh` tokens** — the `gh` CLI recovers its token from the system Keychain Access, not from `~/.config/gh/`. The `COPILOT_GITHUB_TOKEN` env var is the only reliable override.
- **`gho_*` tokens only** — Copilot API rejects fine-grained PATs (`github_pat_*`) with `HTTP 400: Personal Access Tokens are not supported for this endpoint`. You must use the OAuth device code flow.
- **PKCE state persistence** — `--auth-url` saves PKCE state to `google_oauth_pending.json`. If you regenerate the URL after a timeout, the old pending state is overwritten and the old URL won't exchange.
- **`timeout` not available on macOS** — macOS doesn't ship GNU `coreutils`. Use `gtimeout` from `brew install coreutils`, or omit the wrapper since the Python call blocks naturally.

---

## Safety Notes

- **Never store `COPILOT_GITHUB_TOKEN` in shell history** — the `echo` command will leak it to `.bash_history` / `.zsh_history`. Use the agent's `write_file` tool instead.
- **Google client secret is desktop-app type** — it's not a web secret. It's safe to store locally, but don't commit it to git.
- **Revoke access at any time** — users can revoke Google tokens at https://myaccount.google.com/permissions and Copilot access via GitHub Settings → Applications → Authorized OAuth Apps.
- **Test user limit** — Google Cloud projects in Testing mode support up to 100 test users. After that, the app must go through verification or switch to a different project.

---

## Failures Overcome

1. **`gh` token cannot be cleared by deleting files** — On macOS, `gh` stores its token in the system Keychain Access. Deleting `~/.config/gh/` has no effect. The fix is to set `COPILOT_GITHUB_TOKEN` in `.env`, which takes priority over the keychain.

2. **Fine-grained PATs don't work with Copilot API** — `github_pat_*` tokens return `HTTP 400`. You must use the OAuth device code flow to get a `gho_*` token.

3. **"403: access_denied" on Google auth** — The Google Cloud project is in Testing mode and the user's email hasn't been added as a test user. Add them at `console.cloud.google.com/auth/audience`, then generate a fresh auth URL.

4. **Token exchange fails "invalid_grant"** — The auth code expired (they last ~5 minutes) or was already used. Generate a fresh URL and have the user try again immediately.

5. **Scopes can't be reduced without revocation** — If you authenticated with full read-write scopes and want to switch to read-only, you must run `--revoke` first, then re-auth with the narrower scopes.

6. **`write_file` vs `echo >>` for `.env`** — Using shell redirection in an agent approval flow can silently lose content. Always use `write_file` with the complete file content when modifying `.env` through the agent.

7. **Profile-based paths are easy to get wrong** — Always confirm the profile name in the path. `~/.hermes/profiles/<typo>/google_client_secret.json` won't be found by the setup script for the intended profile.
