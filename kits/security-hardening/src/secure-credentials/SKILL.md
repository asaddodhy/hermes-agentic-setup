---
name: secure-credentials
description: "Security-first operations: credentials, secrets, network exposure, data safety, and safe defaults for every session."
version: 2.0.0
author: Hermes Agent (enforced by user security policy)
metadata:
  hermes:
    tags: [security, credentials, ssh, passwords, secrets, network, data-safety]
    priority: critical
---

# Security-First Operations

This skill governs **every** terminal command, file write, config change, and network operation. Before acting, check the relevant section below.

---

## 1. Credentials & Secrets — NEVER on the Command Line

Inline passwords, tokens, API keys, or secrets in a command string are visible to: `ps aux` (any user on the machine), shell history, system audit logs, CI output, and other users on the same host.

### ❌ Prohibited patterns

| Pattern | Risk |
|---------|------|
| `sshpass -p PASSWORD ssh ...` | Plaintext password in process table |
| `mysql -pPASSWORD` | Database credential in ps |
| `curl -u user:password ...` | HTTP Basic auth on CLI |
| `export KEY=*** && command` | Secret in env on same line |
| `--password x --token y` | Credential flag on command line |
| `PGPASSWORD=*** psql ...` | Env var set inline |

### ✅ Safe alternatives

**SSH** — Use SSH keys (already configured for remote hosts):
```bash
ssh user@host                   # key-based
ssh -i ~/.ssh/key user@host    # explicit key
```

**Databases** — Config files or prompt:
```bash
mysql --defaults-file=~/.my.cnf
mysql -u user -p               # interactive prompt
```

**API credentials** — Env files or secret managers:
```bash
source .env && command          # read from file
read -s KEY && export KEY && command  # prompt
```

**HTTP Basic Auth** — `.netrc`:
```bash
# ~/.netrc:
# machine example.com login user password secret
curl -n https://example.com
```

---

## 2. Secrets in Files & Code

| ❌ Never | ✅ Instead |
|----------|-----------|
| Hardcode API keys in source | Use env vars / `.env` / secret manager |
| Commit `.env` to git | Add to `.gitignore` |
| Write secrets world-readable | `chmod 600` or `0400` |
| Log secrets to stdout/files | Redact before logging |

---

## 3. Network & Exposure

| ❌ Never | ✅ Instead |
|----------|-----------|
| Bind to `0.0.0.0` without need | Bind to `127.0.0.1` |
| Expose ports unnecessarily | Only what's needed |
| Plain HTTP for sensitive data | HTTPS/WSS |
| Open SSH password auth | Key-only auth |
| SSH keys without passphrase | Use passphrase |

---

## 4. File & Data Safety

| ❌ Never | ✅ Instead |
|----------|-----------|
| `rm -rf /` or wildcard deletes | Target precise paths |
| `chmod -R 777` | Minimal permissions |
| `curl ... | bash` without review | Download, inspect, execute |
| Untrusted installs as root | Non-root user, verify sources |
| Write to `/etc/` unapproved | `~/.local/` or project dirs |

---

## 5. System & Config

| ❌ Never | ✅ Instead |
|----------|-----------|
| Disable firewall/security | Work within protections |
| Credentials in committed config | Env vars or vault |
| Skip TLS verification | Fix cert issues properly |

---

## 6. Git & Version Control

| ❌ Never | ✅ Instead |
|----------|-----------|
| Commit secrets/tokens/passwords | `.gitignore` + pre-commit hooks |
| Force-push to shared branches | `--force-with-lease` if needed |
| Commit large binaries | Use Git LFS |

---

## Pre-Action Checklist

For every command, file write, config change, or network operation:
- [ ] Credentials or secrets involved?
- [ ] On CLI? Use file/env/key/prompt instead?
- [ ] Exposing something unnecessarily?
- [ ] Destructive or irreversible?
- [ ] Comfortable in a security audit?

---

## Enforcement

This machine has a Tirith security policy at `~/.tirith/policy.yaml` that enforces:
- `sshpass -p` → BLOCKED at runtime
- `curl -u user:password` → BLOCKED
- Inline credential env vars → WARNED

Plus Tirith's built-in rules for pipe-to-shell, credential file sweeps, and terminal injection.

`approvals.mode: smart` is also active — the auxiliary LLM catches anything the regex misses.
