---
name: ssh-key-auth
description: "Set up SSH key-based authentication between two machines for cross-machine Hermes Agent communication, with SSH config shortcuts and connection validation."
version: 1.0.0
author: dodhya
models:
  primary: deepseek-v4-flash-free via opencode-zen
  required_models: []
services:
  tailscale:
    required: false
    description: "Optional — provides an encrypted fallback (Tailscale IP) if LAN is unavailable. Install via Kit 1 (tailscale-userspace) before this kit if you want it."
    setup: "Kit 1 — tailscale-userspace"
parameters: {}
environment:
  os: [macos]
  homebrew: true
  hermes_version: ">=0.1.0"
src:
  fileManifest: []
  note: "This kit is entirely procedural — no source files to install. Follow the steps in order."
---

## Goal

Establish passwordless SSH key authentication between a local machine (control node) and a remote machine (worker/node) so that Hermes Agent can execute cross-machine terminal commands, file transfers, and automation tasks without interactive password prompts. The result is a secure, scriptable, and reproducible SSH trust relationship.

## When to Use

- **Setting up a multi-machine Hermes cluster** — local agent on Machine A talks to remote shell/SDK on Machine B
- **After a fresh macOS install** on either side — keys and `known_hosts` are ephemeral
- **Replacing deprecated password-based SSH** with key-only authentication
- **Recovering from a compromised key** — rotate the key pair and re-deploy
- **Onboarding a new remote node** into an existing Hermes agentic network
- **Before running higher-level kits** (e.g., hermes-api-server, hermes-mcp-bridge) that depend on cross-machine connectivity

## Setup

### What you need

| Item | Detail |
|------|--------|
| Local machine (control) | macOS, user `dodhya`, hostname `mb16` |
| Remote machine (node) | macOS, user `asadpreuss-dodhy`, hostname `mb14` (N719HT) |
| LAN connection | Remote reachable at `192.168.1.200` (direct, best performance) |
| Optional — Tailscale | Remote reachable at `100.97.232.91` (encrypted, works across subnets) |
| Remote must be on | Powered on, connected to network, SSH enabled (System Settings → General → Sharing → Remote Login) |
| Hermes profile | Team-manager profile (this session). SSH config is **machine-wide**, not per-profile. |
| Prerequisite kit | `tailscale-userspace` (Kit 1) — optional but recommended for encrypted fallback |

### What this kit produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| Ed25519 key pair | `~/.ssh/id_ed25519` + `id_ed25519.pub` | Modern, fast, secure key type |
| Remote authorized key | `~/.ssh/authorized_keys` (on remote) | Grants passwordless access |
| Local known hosts entry | `~/.ssh/known_hosts` | Host key verification (TOFU) |
| SSH config alias | `~/.ssh/config` | Shortcuts like `ssh mb14` instead of full user@host |

### Important about `~/.ssh/config`

The local machine's `~/.ssh/config` already contains a Gitpod Flex include directive managed by Gitpod. This kit appends a host block for the remote machine — it does **not** overwrite or modify the Gitpod-managed section. The config file will look like:

```
# Gitpod Flex — managed, do not edit
Include ~/.ssh/gitpod_flex_config

# Custom Hermes hosts (appended by this kit)
Host mb14
    HostName 192.168.1.200
    User asadpreuss-dodhy
    IdentityFile ~/.ssh/id_ed25519
```

The `Include` directive is first, so Gitpod config loads first; Hermes-specific hosts are appended after.

## Steps

### Step 1: Generate an Ed25519 SSH key pair

Generate a key pair on the **local machine** (`mb16`). Ed25519 is preferred over RSA for its speed, security, and smaller key size.

```bash
ssh-keygen -t ed25519 -C "hermes-mb16-to-mb14" -f ~/.ssh/id_ed25519
```

You will be prompted:

```
Generating public/private ed25519 key pair.
Enter passphrase (empty for no passphrase):
Enter same passphrase again:
```

**Leave the passphrase empty** for automated Hermes cross-machine communication. The key file is already protected by macOS file permissions (`chmod 600`), and the remote is on a trusted LAN.

✅ Verify the key pair exists:

```bash
ls -la ~/.ssh/id_ed25519*
```

Expected output (dates vary):

```
-rw-------  1 dodhya  staff  464 Jun 17 10:00 /Users/dodhya/.ssh/id_ed25519
-rw-r--r--  1 dodhya  staff  104 Jun 17 10:00 /Users/dodhya/.ssh/id_ed25519.pub
```

> 🔁 **Already have a key?** If `~/.ssh/id_ed25519` already exists, skip this step. Verify with `ssh-keygen -lf ~/.ssh/id_ed25519` that it's an Ed25519 key. If it's RSA (`ssh-rsa` prefix), consider generating a fresh Ed25519 key for best practice.

---

### Step 2: Copy the public key to the remote machine

Use `ssh-copy-id` to install the public key into the remote's `~/.ssh/authorized_keys`. This requires one interactive password login via LAN.

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub asadpreuss-dodhy@192.168.1.200
```

You will be prompted for the remote user's **login password** (not a passphrase — the key has none):

```
/usr/bin/ssh-copy-id: INFO: attempting to log in with the new key(s), to filter out any that are already installed
/usr/bin/ssh-copy-id: INFO: 1 key(s) remain to be installed -- if you are prompted now it is the new key, but you can also use the existing password
asadpreuss-dodhy@192.168.1.200's password:
```

Enter the macOS login password for `asadpreuss-dodhy` on `mb14`.

✅ On success you'll see:

```
Number of key(s) added: 1

Now try logging into the machine, with:   "ssh 'asadpreuss-dodhy@192.168.1.200'"
and check to make sure only the key(s) you wanted were added.
```

> ⚠️ **If `ssh-copy-id` is not installed** (some minimal macOS setups lack it), install it via Homebrew or use the manual method:
>
> ```bash
> cat ~/.ssh/id_ed25519.pub | ssh asadpreuss-dodhy@192.168.1.200 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
> ```

---

### Step 3: Test passwordless SSH connection

Verify the key works without a password prompt.

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new asadpreuss-dodhy@192.168.1.200 "hostname; whoami; uptime"
```

Expected output (no password prompt):

```
mb14
asadpreuss-dodhy
10:30  up 2 days, 4:15, 2 users, load averages: 1.2 1.0 0.8
```

Flags explained:

| Flag | Purpose |
|------|---------|
| `-o BatchMode=yes` | Fail immediately if SSH asks for a password (key auth enforced) |
| `-o StrictHostKeyChecking=accept-new` | Auto-accept the remote host key on first connection (TOFU) |

The first connection will prompt with a host key fingerprint:

```
The authenticity of host '192.168.1.200 (192.168.1.200)' can't be established.
ED25519 key fingerprint is SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Type **yes** to accept it. This writes the host key to `~/.ssh/known_hosts`.

✅ Verify the known hosts entry:

```bash
ssh-keygen -lf ~/.ssh/known_hosts
```

Expected output (3 entries for the 192.168.x.x hosts):

```
256 SHA256:xxx 192.168.1.200 (ED25519)
256 SHA256:yyy 192.168.1.201 (ED25519)
256 SHA256:zzz 192.168.1.202 (ED25519)
```

---

### Step 4: Test via Tailscale (optional, encrypted fallback)

If Tailscale is running on both machines, test the connection over the encrypted Tailscale IP:

```bash
ssh -o BatchMode=yes asadpreuss-dodhy@100.97.232.91 "hostname; uptime"
```

This path uses the same key — `~/.ssh/id_ed25519` is a machine-wide identity and works regardless of which IP or interface the remote is reached on.

✅ The Tailscale route is valuable when LAN is unavailable (different subnet, coffee shop, remote work) but both machines are logged into the same Tailscale tailnet.

---

### Step 5: Create SSH config shortcuts

Append a host block to `~/.ssh/config` so you can connect with a simple `ssh mb14` instead of the full `user@host`. The config file already has a Gitpod Flex include directive at the top; we add Hermes hosts after it.

```bash
cat >> ~/.ssh/config << 'EOF'

# Hermes: mb14 remote node
Host mb14
    HostName 192.168.1.200
    User asadpreuss-dodhy
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 3

# Hermes: mb14 via Tailscale (encrypted fallback)
Host mb14-ts
    HostName 100.97.232.91
    User asadpreuss-dodhy
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 30
    ServerAliveCountMax 3
EOF
```

✅ Verify the config:

```bash
ssh mb14 "hostname"
ssh mb14-ts "hostname"
```

Both should return `mb14` without a password prompt.

---

### Step 6: Hardening — disable password auth on the remote (optional but recommended)

Once key-based auth is confirmed working, disable SSH password authentication on the remote machine to block brute-force attacks.

On the **remote** (`mb14`), edit `/etc/ssh/sshd_config`:

```bash
# Run this on mb14 (ssh mb14 first)
sudo sed -i '' 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i '' 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo launchctl unload /System/Library/LaunchDaemons/ssh.plist 2>/dev/null; sudo launchctl load -w /System/Library/LaunchDaemons/ssh.plist
```

Or equivalently via a one-liner from the local machine:

```bash
ssh -t mb14 "sudo sed -i '' 's/^#*PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && sudo launchctl kickstart -k system/com.openssh.sshd"
```

✅ After this, `ssh -o PasswordAuthentication=yes -o BatchMode=no mb14` should fail with "Permission denied (publickey)" — key-only auth is enforced.

> ❗ **Do not** disable password auth until you have verified key-based login works (Steps 3–5). Locking yourself out without a working key is difficult to recover from without physical access.

---

### Step 7: Validate the setup end-to-end for Hermes

Confirm that Hermes can use the SSH connection from within a terminal action. Run a command that exercises the key-based path:

```bash
# Hermes-style cross-machine command
ssh mb14 "echo 'Hermes cross-machine communication OK: \$(hostname)'; df -h / | tail -1"
```

Expected output:

```
Hermes cross-machine communication OK: mb14
/dev/disk1s1  460Gi  200Gi  260Gi  44% /
```

Also test a file copy to confirm SCP/rsync works for artifact transfer:

```bash
scp mb14:~/.ssh/authorized_keys /tmp/remote-authorized-keys-check
cat /tmp/remote-authorized-keys-check | head -1
# Should show: ssh-ed25519 AAA... (your public key)
```

## Constraints

- **SSH key passphrase must be empty** for unattended Hermes automation. If you set a passphrase, `ssh-agent` must be running and the key added (`ssh-add ~/.ssh/id_ed25519`) before Hermes can use it.
- **This kit sets up key auth one way** (local→remote). Hermes currently uses a local agent that connects out to remotes. If you need bidirectional trust (remote→local), repeat Steps 1–5 from the remote machine with a separate key pair.
- **`~/.ssh/config` has a Gitpod Flex include directive** already present. The `cat >>` append in Step 5 adds content *after* it, which is correct — `Include` directives load first and subsequent `Host` blocks can override settings.
- **macOS SIP (System Integrity Protection)** does not interfere with `~/.ssh/` but may prevent modifying `/etc/ssh/sshd_config` if the remote is a sealed system volume — use `sudo` and the `launchctl` restart path shown.
- **Multiple SSH keys** on the same agent can cause authentication failures if more than 5 keys are offered before the correct one. The `IdentityFile` directive in `~/.ssh/config` avoids this by specifying exactly which key to use for `mb14`.
- **Tailscale performance** is slightly lower than direct LAN due to WireGuard encryption overhead. Use the LAN IP for latency-sensitive Hermes operations; use the Tailscale IP when off-subnet.

## Safety Notes

- **Leave the passphrase empty only** if the machines are on a trusted LAN (home/office network) and the key file is protected by filesystem permissions (`~/.ssh/` is `chmod 700`, key files are `chmod 600`).
- **Never share the private key** (`~/.ssh/id_ed25519`). Anyone with it can authenticate as `dodhya` to `asadpreuss-dodhy` on `mb14`. Treat it like a password.
- **`ssh-copy-id` transmits the password** over the network in plaintext on the first call — but only that once. After the key is deployed, password auth should be disabled.
- **Lock yourself out risk**: If you disable password auth on the remote (Step 6) without a working key, you'll need physical access or a recovery method (e.g., Tailscale SSH, ARD, or a bootable USB) to regain entry. Always verify the key first.
- **Known hosts change detection**: If the remote machine is rebuilt or its host key changes, SSH will refuse the connection with a `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!` error. Remove the old key with `ssh-keygen -R 192.168.1.200` and reconnect.
- **Rotate keys periodically**: For production Hermes setups, generate fresh keys every 6–12 months. Use the same steps — generate, copy, test, validate.

## Failures Overcome

1. **`ssh-copy-id` not installed** — Some macOS minimal builds omit it. The manual `cat pubkey | ssh mkdir + cat >>` fallback in Step 2 works on any POSIX system.
2. **Gitpod Flex config collision** — The `~/.ssh/config` already has `Include ~/.ssh/gitpod_flex_config` at the top. Our append writes *after* it, which is the correct position. If the Gitpod managed section were last, it would override our `Host` blocks. The `Host ... HostName ... User ... IdentityFile` block we write is valid because it comes after the `Include`.
3. **Multiple key offering timeout** — If the SSH agent has many keys loaded, the server may disconnect before the correct key is tried. Fixed by specifying `IdentityFile ~/.ssh/id_ed25519` in `~/.ssh/config`.
4. **Permission denied on `/etc/ssh/sshd_config` editing** — macOS's sealed system volume (SSV) in recent macOS versions may reject writes even with `sudo`. The workaround is to edit via `sudo vim` after disabling SSV protections, or skip Step 6 if the remote is a sealed system.
5. **Tailscale IP unreachable on first test** — Tailscale must be authenticated and connected on both machines. Verify with `tailscale status` on both sides. The 100.x.x.x IP is assigned dynamically and stable within a tailnet.
6. **`StrictHostKeyChecking=accept-new` vs `StrictHostKeyChecking=no`** — Use `accept-new` to auto-accept only the first connection. Using `no` disables host key checking entirely, opening a MITM attack vector. Hermes should never use `StrictHostKeyChecking=no` for production.

## Validation

After completing all steps, this checklist confirms the SSH key auth setup is fully operational:

- [ ] `~/.ssh/id_ed25519` exists — private key present and permissions `600`
- [ ] `~/.ssh/id_ed25519.pub` exists — public key present
- [ ] `ssh -o BatchMode=yes mb14 "hostname"` returns `mb14` without any password prompt
- [ ] `ssh -o BatchMode=yes asadpreuss-dodhy@100.97.232.91 "hostname"` returns `mb14` (Tailscale route)
- [ ] `~/.ssh/config` contains `Host mb14` block with correct HostName, User, IdentityFile
- [ ] `~/.ssh/config` contains `Host mb14-ts` block for Tailscale fallback
- [ ] `ssh mb14 "uptime"` — remote uptime displayed, no password asked
- [ ] `scp mb14:~/.ssh/authorized_keys /dev/null` — SCP works (file transfer ready)
- [ ] Known hosts: `ssh-keygen -lf ~/.ssh/known_hosts` shows 3+ entries for 192.168.x.x hosts
- [ ] **Optional** — Password auth disabled on remote: `ssh -o PasswordAuthentication=yes -o PreferredAuthentications=password mb14` returns `Permission denied (publickey)`
