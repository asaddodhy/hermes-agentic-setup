#!/bin/bash
# Generate the README kit inventory table from all kits/*/kit.md frontmatter.
# Reads kit directories, extracts name and description from YAML frontmatter,
# and replaces content between <!-- KIT-TABLE:START --> and <!-- KIT-TABLE:END --> markers.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
KITS_DIR="$REPO_DIR/kits"
README="$REPO_DIR/README.md"

cd "$REPO_DIR"

# Collect kit entries as: name|description|dirname
entries=()
for kitfile in "$KITS_DIR"/*/kit.md; do
    [ -f "$kitfile" ] || continue
    dirname=$(basename "$(dirname "$kitfile")")
    name=$(grep -m1 '^name:' "$kitfile" | sed 's/^name: *//')

    # Extract description, handling multi-line YAML (>- block scalar) and quoted values
    desc=""
    in_desc=false
    while IFS= read -r dline; do
        # Detect start of description line
        if echo "$dline" | grep -q '^description:'; then
            in_desc=true
            # Strip "description:" prefix, optional quotes
            desc=$(echo "$dline" | sed -E 's/^description:[[:space:]]*"?//' | sed -E 's/"$//')
            # Check for >- folded scalar marker
            if [ "$desc" = ">-" ]; then
                desc=""
            fi
            continue
        fi

        # If we're past the description line, look for continuation lines (indented)
        if $in_desc; then
            # If line starts with whitespace, it's a continuation
            if echo "$dline" | grep -q '^[[:space:]]'; then
                trimmed=$(echo "$dline" | sed -E 's/^[[:space:]]+//')
                [ -z "$trimmed" ] && break
                [ -z "$desc" ] && desc="$trimmed" || desc="$desc $trimmed"
            else
                # Not indented anymore — description is done
                break
            fi
        fi
    done < <(tail -n +2 "$kitfile" | head -20)

    # Truncate long descriptions to ~80 chars for the table
    if [ ${#desc} -gt 80 ]; then
        desc="${desc:0:77}..."
    fi
    entries+=("$name|$desc|$dirname")
done

# Sort alphabetically by name
IFS=$'\n' sorted=($(sort <<<"${entries[*]}")); unset IFS

# Build the table into a temp file
table_file=$(mktemp)
# Emit header row + separator
printf "| # | Kit | What it does | Dependencies | Backup status |\n" > "$table_file"
printf "|---|---|---|---|---|\n" >> "$table_file"
count=0
for entry in "${sorted[@]}"; do
    count=$((count + 1))
    IFS='|' read -r name desc dirname <<< "$entry"
    printf "| %d | **[%s](kits/%s/kit.md)** | %s | | |\n" "$count" "$name" "$dirname" "$desc" >> "$table_file"
done

# Generate final README with awk
awk -v table_file="$table_file" '
/<!-- KIT-TABLE:START -->/ {
    print
    while ((getline line < table_file) > 0) print line
    close(table_file)
    skip = 1
    next
}
/<!-- KIT-TABLE:END -->/ {
    skip = 0
    print
    next
}
!skip { print }
' "$README" > "$README.tmp" && mv "$README.tmp" "$README"

rm -f "$table_file"

echo "✅ README.md kit table updated ($count kits)"
