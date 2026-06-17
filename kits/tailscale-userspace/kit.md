---
name: tailscale-userspace
description: "Set up Tailscale in userspace (no-root) mode for cross-machine Hermes agent mesh networking."
version: 1.0.0
author: dodhya
models:
  primary: deepseek-v4-flash-free via opencode-zen
  required_models: []
services:
  tailscale:
    required: true
    description: "VPN mesh — Tailscale free tier. Installed via Homebrew: brew install tailscale."
    setup: "brew install tailscale. No GUI app needed — CLI-only userspace mode with custom socket/state paths."
parameters:
  tailscale.userspace.socket: ~/.hermes/tailscale.sock
  tailscale.userspace.state: ~/.hermes/tailscale-state.json
  tailscale.userspace.daemon_binary: /opt/homebrew/opt/tailscale/bin/tailscaled
  tailscale.userspace.client_binary: /opt/homebrew/bin/tailscale
environment:
  os: [macos]
  homebrew: true
  hermes_version: ">=0.1.0"
src:
  fileManifest:
    - path: src/io.tailscale.userspace.plist
      role: "Launchd plist — auto-starts tailscaled on login with userspace networking and custom socket/state paths"
      destination: ~/Library/LaunchAgents/io.tailscale.userspace.plist
    - path: src/tailscale-helper.sh
      role: "Shell helper — convenience aliases (ts, ts-up, ts-st, tsd) for managing Tailscale with the custom socket"
      destination: ~/.hermes/bin/tailscale-helper.sh
---

## Goal

Install and configure Tailscale in userspace (no-root/CLI-only) mode on macOS, with a custom unix socket under `~/.hermes/`, so that multiple Hermes Agent instances can communicate securely over a tailnet VPN mesh. No GUI app, no sudo required.

## When to Use

- **New machine setup** — run this kit after Homebrew and before any cross-machine Hermes features (MCP, API Server, SSH/tmux)
- **After a macOS reinstall** — Tailscale must be reinstalled and re-authenticated
- **When migrating profiles** — the socket/state paths are referenced by the `team-manager` profile
- **Expanding the mesh** — add a new machine to an existing tailnet for multi-agent orchestration
- **Before any networking kit** — this is kit #1 in the bootstrap sequence: (1) tailscale-userspace → (2) ssh-key-auth → (3) hermes-mcp-bridge + hermes-api-server → (4) security-hardening

## Setup

### What you need

- macOS machine with Homebrew installed
- A Tailscale account (free tier — up to 100 devices)
- Browser access for initial Tailscale authentication (one-time)
- Hermes Agent installed (any profile)

### What this kit installs

| File | Destination | Purpose |
|------|-------------|---------|
| `src/io.tailscale.userspace.plist` | `~/Library/LaunchAgents/io.tailscale.userspace.plist` | Launchd plist — auto-starts `tailscaled` on login with `--tun=userspace-networking` and the custom socket |
| `src/tailscale-helper.sh` | `~/.hermes/bin/tailscale-helper.sh` | Shell helper — `ts`, `ts-up`, `ts-st`, `tsd` convenience aliases |

### Files this kit creates

| Path | Purpose |
|------|---------|
| `~/.hermes/tailscale.sock` | Unix socket for the tailscaled daemon (user-writable, no root) |
| `~/.hermes/tailscale-state.json` | Persistent Tailscale state — authentication keys, node info, profile |

## Steps

### Step 1: Install Tailscale via Homebrew

```bash
brew install tailscale
```

This installs both binaries:
- `/opt/homebrew/bin/tailscale` — CLI client
- `/opt/homebrew/opt/tailscale/bin/tailscaled` — daemon

Verify the installation:

```bash
tailscale version
```

Expected output:
```
1.98.x
  tailscale commit: ...
  go version: go1.26.x
```

### Step 2: Create the Hermes state directory

```bash
mkdir -p ~/.hermes
```

### Step 3: Start the tailscaled daemon

The default socket at `/var/run/tailscaled.socket` requires root. Run in userspace mode with a custom socket under your home directory.

**⚠️ Use full absolute paths.** The tilde `~` is NOT expanded by tailscaled when passed as part of a `--key=value` flag (e.g., `--state=~/.hermes/...` passes the literal `~`).

Direct invocation (works in any shell):

```bash
/opt/homebrew/opt/tailscale/bin/tailscaled \
  --tun=userspace-networking \
  --state=/Users/$(whoami)/.hermes/tailscale-state.json \
  --socket=/Users/$(whoami)/.hermes/tailscale.sock
```

Keep this running in the background. Options:

**Option A — Launchd plist (recommended):** Auto-starts on login:

```bash
cp src/io.tailscale.userspace.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/io.tailscale.userspace.plist
```

**Option B — Hermes background terminal:** Start from within Hermes:

```bash
terminal(background=true): /opt/homebrew/opt/tailscale/bin/tailscaled \
  --tun=userspace-networking \
  --state=/Users/$(whoami)/.hermes/tailscale-state.json \
  --socket=/Users/$(whoami)/.hermes/tailscale.sock \
  > /tmp/tailscaled.log 2>&1
```

**Option C — brew services:** Start as a standard launchd service:

```bash
brew services start tailscale
```

> ⚠️ `brew services start tailscale` may fail with exit code 1 on some macOS configurations because the default Homebrew plist does not include `--tun=userspace-networking` or custom socket flags. If it fails, use Option A or B instead.

Verify the daemon is running:

```bash
ls -la ~/.hermes/tailscale.sock
# → srw-rw-rw-@ ... /Users/dodhya/.hermes/tailscale.sock

ps aux | grep tailscaled | grep -v grep
# → ... /opt/homebrew/opt/tailscale/bin/tailscaled --tun=userspace-networking --state=...
```

### Step 4: Authenticate with Tailscale

Every `tailscale` CLI command must include `--socket` when using a custom socket path. Without it, you'll get:

```
failed to connect to local Tailscale service; is Tailscale running?
```

**Cleanest authentication workflow:**

```bash
# 1. Get the login URL (non-blocking)
tailscale --socket ~/.hermes/tailscale.sock status
# → "Log in at: https://login.tailscale.com/a/..."

# 2. Start `up` in background (so it catches the auth callback)
tailscale --socket ~/.hermes/tailscale.sock up &
```

3. **Open the URL** printed by `status` in your browser and log in with your Tailscale account.
4. The background `up` process detects auth completion and exits with code 0.

Alternatively, run `up` in a separate terminal:

```bash
tailscale --socket ~/.hermes/tailscale.sock up
```

This blocks until the browser login completes.

### Step 5: Install the shell helper (optional)

```bash
mkdir -p ~/.hermes/bin
cp src/tailscale-helper.sh ~/.hermes/bin/tailscale-helper.sh
chmod +x ~/.hermes/bin/tailscale-helper.sh
```

Add to your shell init (`~/.zshrc` or `~/.bashrc`):

```bash
source ~/.hermes/bin/tailscale-helper.sh
```

After sourcing, you get:

| Command | What it does |
|---------|-------------|
| `ts status` | `tailscale --socket ~/.hermes/tailscale.sock status` |
| `ts up` | `tailscale --socket ~/.hermes/tailscale.sock up` |
| `ts-up` | Status → background `up` → open URL workflow |
| `ts-st` | Shortcut for `ts status` |
| `tsd` | Start tailscaled in background with proper arguments |

### Step 6: Verify connectivity

```bash
tailscale --socket ~/.hermes/tailscale.sock status
```

Expected output (example with two machines):

```
100.120.204.56  mb16             asad.h.d@  macOS    -
100.97.232.91   mb14             asad.h.d@  macOS    -
100.126.164.63  pixel-10-pro-xl  asad.h.d@  android  offline, last seen 2d ago
```

- **`-`** (dash) → directly connected, active
- **`offline, last seen N ago`** → not currently reachable

Test TCP reachability (ICMP ping does NOT work in userspace mode — see Constraints):

```bash
# Test SSH port on a remote machine (replace with your machine's IP)
nc -zv 100.x.x.x 22

# Test Hermes API Server port
nc -zv 100.x.x.x 8642

# Test MCP port
nc -zv 100.x.x.x 8001
```

### Step 7: Configure Hermes profile for mesh networking

If using the `team-manager` profile, Tailscale enables cross-machine Hermes operations. The profile stores the socket/state paths in memory for reference. Key configuration:

- **MCP Server**: binds to `0.0.0.0:8001` on the remote machine, reachable via `100.x.x.x:8001`
- **API Server Gateway**: binds to `0.0.0.0:8642`, reachable via `100.x.x.x:8642`
- **SSH**: connect by Tailscale IP (`ssh user@100.x.x.x`) or hostname (`ssh user@hostname.tailnet.ts.net`)

No special Tailscale-side config changes are needed — the tailnet provides L3 connectivity. All Hermes services use plain HTTP over the encrypted tailnet.

## Constraints

- **ICMP ping does NOT work in userspace mode.** `--tun=userspace-networking` uses a userspace TUN implementation that does not support ICMP. Use `nc -zv`, `curl`, or SSH to verify connectivity instead.
- **Every `tailscale` CLI command needs `--socket <path>`** when using a custom socket. The `TS_SOCKET` environment variable is NOT supported by the Tailscale CLI — the `--socket` flag is required.
- **Tilde expansion fails in `--key=value` flags.** Tailscaled does not expand `~` when passed as `--state=~/.hermes/file`. Always use full absolute paths (`/Users/username/...`).
- **`brew services start tailscale` may fail** because the default Homebrew plist does not include `--tun=userspace-networking` or custom socket/state arguments. Use the provided launchd plist or direct invocation instead.
- **Free tier limits:** Up to 100 devices, 3 users. The free tier is sufficient for a multi-machine Hermes mesh.
- **Tailscale SSH requires CLI-only install:** The App Store / sandboxed GUI build does not support the Tailscale SSH server. If you need Tailscale SSH, install via `brew install tailscale` (not the cask) and run in userspace mode.
- **Profile isolation:** If using multiple Hermes profiles, each profile references the same Tailscale daemon (single socket) — there is one tailnet per machine, shared across all profiles.
- **Old state may persist after reinstall:** Even with `--state` pointing to a new file, tailscaled may use `~/.local/share/tailscale/` as the system state directory. If old state interferes, remove it: `rm -rf ~/.local/share/tailscale`

## Safety Notes

- **Tailscale traffic is end-to-end encrypted.** Plain HTTP between Hermes instances over the tailnet is safe — no TLS needed for inter-agent traffic inside the tailnet.
- **The tailscaled socket (`tailscale.sock`) is world-readable/writable** (`srw-rw-rw-`) by default. On a multi-user machine, any local user could interact with the tailnet. Restrict permissions if this is a concern: `chmod 600 ~/.hermes/tailscale.sock`.
- **Tailscale state file contains private keys.** Protect it: `chmod 600 ~/.hermes/tailscale-state.json`.
- **Do NOT expose Hermes API Server or MCP ports to the public internet.** Bind to `0.0.0.0` only on machines that are on a trusted network (LAN or tailnet). For internet exposure, add a reverse proxy with TLS (Caddy, Nginx + Let's Encrypt).
- **Tailscale free tier has no access controls.** All nodes on the same tailnet can reach each other. For multi-tenant isolation, consider separate tailnets or ACLs (available on paid plans).
- **The `--accept-hooks` flag on the Hermes gateway auto-approves shell operations** — understand this risk when using the API server gateway over the tailnet.

## Failures Overcome

1. **Tilde expansion in `--state=~/.hermes/file`** — The `=` prevents shell expansion. Tailscaled receives the literal `~`. Always use full absolute paths. Mitigated by using `$(whoami)` in command examples.

2. **`brew services start tailscale` fails silently** — The default Homebrew plist at `/opt/homebrew/opt/tailscale/homebrew.mxcl.tailscale.plist` does not pass `--tun=userspace-networking`, `--state`, or `--socket`. On macOS it starts tailscaled with the default socket at `/var/run/tailscaled.socket`, which fails with a permission error. Solved by providing a custom launchd plist through this kit.

3. **`TS_SOCKET` env var not supported** — Some Tailscale documentation references `TS_SOCKET` but the CLI binary does not respect it. Every command must include `--socket` explicitly. Solved by the `ts()` shell alias in the helper script.

4. **Persistent old state at `~/.local/share/tailscale`** — After reinstalling or switching to userspace mode, the old system state directory may interfere. Tailscaled logs show: `logpolicy: using system state directory "/Users/dodhya/.local/share/tailscale"`. Remove this if authentication behaves unexpectedly: `rm -rf ~/.local/share/tailscale`.

5. **"context canceled" after login URL printed** — `tailscale up` times out or gets canceled while waiting for browser login. Solved by the workflow: run `status` first to get the login URL, then run `up` in the background, then visit the URL in a browser.

6. **Hardware attestation warning** — On macOS, tailscaled logs: `policy requires hardware attestation, but device does not support it`. This is cosmetic — Tailscale continues to work normally in userspace mode.

7. **Tailscale SSH not available in sandboxed GUI builds** — Users who installed Tailscale via the App Store cannot use `tailscale up --ssh`. The fix is to install via Homebrew CLI-only and run in userspace mode (this kit ensures that).

## Validation

After completing all steps, this checklist confirms success:

- [ ] Tailscale installed: `tailscale version` → shows a version number
- [ ] tailscaled daemon running: `ls -la ~/.hermes/tailscale.sock` → socket file exists
- [ ] tailscaled daemon running: `ps aux | grep tailscaled | grep -v grep` → process with `--tun=userspace-networking` and custom socket
- [ ] Authenticated: `tailscale --socket ~/.hermes/tailscale.sock status` → shows tailnet IP and connected nodes
- [ ] TCP reachability: `nc -zv <remote-tailscale-ip> 22` → succeeds (Connection to port 22 succeeded)
- [ ] Helper script installed: `source ~/.hermes/bin/tailscale-helper.sh && ts status` → works (optionally)
- [ ] Launchd plist loaded: `launchctl list | grep io.tailscale.userspace` → shows PID (if using launchd)
- [ ] Tailscale IP known: `tailscale --socket ~/.hermes/tailscale.sock ip -1` → prints the machine's tailnet IP
- [ ] Remote machine visible: `tailscale --socket ~/.hermes/tailscale.sock status` → shows other machine(s) without "offline" label
- [ ] Hermes profile (team-manager) can reach remote: `ping -c 1 -t 2 <remote-tailscale-ip>` → or more accurately, `nc -zv <remote-tailscale-ip> 22` → succeeds
