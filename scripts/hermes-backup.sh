#!/bin/bash
# Hermes Repo Backup Script — v2 (convention-driven)
# Reads paths to back up from discover-paths.sh (or a provided file),
# verifies the repo structure, and creates a timestamped tarball.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TARBALL_NAME="hermes-backup-${TIMESTAMP}.tar.gz"

# --- Determine backup destination ---
NETWORK_DRIVE="/Volumes/Seagate_Backup_Plus_Drive/NAS/Hermes Backup"
LOCAL_FALLBACK="$HOME/Documents/Hermes Backup"

if [ -d "$NETWORK_DRIVE" ]; then
    DEST="$NETWORK_DRIVE"
    DRIVE_STATUS="connected"
else
    DEST="$LOCAL_FALLBACK"
    DRIVE_STATUS="disconnected"
    mkdir -p "$DEST"
fi

TARBALL_PATH="$DEST/$TARBALL_NAME"

echo "📦 Hermes Repo Backup v2"
echo "   Timestamp: $TIMESTAMP"
echo "   Repo:      $REPO_DIR"
echo "   Drive:     $DRIVE_STATUS ($DEST)"
echo ""

# --- Step 1: Gather paths to back up ---
PATHS_FILE="${1:-}"
if [ -z "$PATHS_FILE" ]; then
    echo "🔍 Running discover-paths.sh to gather paths..."
    PATHS_FILE=$(mktemp)
    "$SCRIPT_DIR/discover-paths.sh" > "$PATHS_FILE"
    CLEANUP_TEMP=true
else
    echo "📄 Reading paths from: $PATHS_FILE"
    CLEANUP_TEMP=false
fi

PATH_COUNT=$(wc -l < "$PATHS_FILE" | xargs)
echo "   Found $PATH_COUNT paths to back up"
echo ""

# --- Step 2: Verify repo structure ---
echo "🔍 Verifying repo structure..."
KIT_COUNT=0
MISSING_KITS=()
for kit_dir in "$REPO_DIR/kits/"*/; do
    kname=$(basename "$kit_dir")
    if [ -f "$kit_dir/kit.md" ]; then
        KIT_COUNT=$((KIT_COUNT + 1))
    else
        MISSING_KITS+=("$kname")
    fi
done

if [ ${#MISSING_KITS[@]} -gt 0 ]; then
    echo "⚠️  Warning: ${#MISSING_KITS[@]} kit(s) missing kit.md:"
    for k in "${MISSING_KITS[@]}"; do echo "     - $k"; done
else
    echo "✅ All $KIT_COUNT kits have kit.md files"
fi

[ -f "$REPO_DIR/README.md" ]               && echo "✅ README.md present"
[ -f "$REPO_DIR/MASTER-RESTORATION.md" ]   && echo "✅ MASTER-RESTORATION.md present"

# Check for KIT-TABLE markers
if grep -q '<!-- KIT-TABLE:START -->' "$REPO_DIR/README.md" 2>/dev/null; then
    echo "✅ README has KIT-TABLE markers (auto-generated table)"
else
    echo "⚠️  README missing KIT-TABLE markers — run update-readme-kits.sh"
fi

echo ""

# --- Step 3: Create tarball ---
echo "🗜️  Creating tarball..."

# Filter to only existing paths
EXISTING_PATHS=()
while IFS= read -r p; do
    # Skip empty lines
    [ -z "$p" ] && continue
    # Expand ~ if present
    eval expanded="$p"
    if [ -e "$expanded" ]; then
        EXISTING_PATHS+=("$expanded")
    else
        echo "   (skipping missing: $p)"
    fi
done < "$PATHS_FILE"

if [ $CLEANUP_TEMP = true ]; then
    rm -f "$PATHS_FILE"
fi

if [ ${#EXISTING_PATHS[@]} -eq 0 ]; then
    echo "❌ No valid paths to back up!"
    exit 1
fi

tar czf "$TARBALL_PATH" "${EXISTING_PATHS[@]}" 2>/dev/null

# Verify tarball
if [ -f "$TARBALL_PATH" ]; then
    SIZE=$(du -sh "$TARBALL_PATH" | cut -f1)
    FILE_COUNT=$(tar tzf "$TARBALL_PATH" 2>/dev/null | wc -l | xargs)
    echo "✅ Created: $TARBALL_PATH"
    echo "   Size:    $SIZE"
    echo "   Files:   $FILE_COUNT"
else
    echo "❌ Failed to create tarball"
    exit 1
fi

echo ""

# --- Step 4: Report ---
echo "📋 Backup Summary"
echo "   Destination:  $DEST"
echo "   Tarball:      $TARBALL_NAME"
echo "   Paths backed: ${#EXISTING_PATHS[@]}"
echo "   Kit count:    $KIT_COUNT"
if [ "$DRIVE_STATUS" = "disconnected" ]; then
    echo ""
    echo "⚠️  NOTE: Network backup drive was NOT connected."
    echo "   Tarball saved to local fallback: $LOCAL_FALLBACK"
    echo "   Connect your Seagate drive and run this script again to copy to the network location."
fi

echo ""
echo "✅ Backup complete."
