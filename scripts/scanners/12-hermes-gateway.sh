#!/bin/bash
# Hermes gateway config — channel_directory.json stores platform registrations
# (Telegram bot token refs, Discord webhook refs, etc.) for all connected platforms.
set -euo pipefail

[ -f "$HOME/.hermes/channel_directory.json" ] && echo "$HOME/.hermes/channel_directory.json"
