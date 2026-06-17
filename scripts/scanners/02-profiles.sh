#!/bin/bash
# All Hermes profiles — entire profile directories (configs, skills, memories, auth)
set -euo pipefail

for profile in "$HOME"/.hermes/profiles/*/; do
    [ -d "$profile" ] && echo "${profile%/}"
done
