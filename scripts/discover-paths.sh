#!/bin/bash
# Discover all paths to back up by running convention scanners.
# Output: one absolute path per line (directories and files).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCANNERS_DIR="$SCRIPT_DIR/scanners"

# Run all .sh scanner scripts (sorted by prefix)
for scanner in "$SCANNERS_DIR"/[0-9]*.sh; do
    [ -f "$scanner" ] || continue
    bash "$scanner" || true
done

# Append custom paths from the .txt file
if [ -f "$SCANNERS_DIR/99-custom-paths.txt" ]; then
    grep -v '^#' "$SCANNERS_DIR/99-custom-paths.txt" | grep -v '^[[:space:]]*$' || true
fi
