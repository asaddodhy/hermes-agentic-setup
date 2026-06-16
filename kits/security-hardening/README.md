# Security Hardening Suite for Hermes Agent

Prevent credential leakage, enforce security best practices, and lock down agent operations with Tirith scanning, smart approvals, and a comprehensive security skill.

> **Who this is for:** Hermes Agent users who want production-grade security on their agent environment.
> **What you get:** Tirith custom rules (blocks sshpass/-u passwords on CLI), smart approvals mode, and a secure-credentials skill that governs every terminal command.
> **Time to install:** ~5 minutes

## Prerequisites

- Hermes Agent (any profile)
- macOS (other OS works but paths may differ)
- No existing `~/.tirith/` policy (or willing to overwrite)

## What's in this kit

```
kits/security-hardening/
├── kit.md                      # This workflow
├── README.md                   # This page
└── src/
    ├── .tirith/policy.yaml     # Custom rules: sshpass, curl -u, inline env creds
    └── secure-credentials/
        └── SKILL.md            # Security-first operations skill (6 domains)
```
