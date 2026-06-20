#!/bin/bash
# Hermes-related launchd LaunchAgents plists — gateways, dashboard, session-indexer, WebUI
# These must be backed up so daemons can be restored without re-running full setup.
set -euo pipefail

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

# All ai.hermes.* plists (gateway, dashboard, session-indexer, per-profile gateways)
for plist in "$LAUNCH_AGENTS"/ai.hermes.*.plist; do
    [ -f "$plist" ] && echo "$plist"
done

# Hermes WebUI plist (com.parantoux.hermes-webui)
[ -f "$LAUNCH_AGENTS/com.parantoux.hermes-webui.plist" ] && echo "$LAUNCH_AGENTS/com.parantoux.hermes-webui.plist"
