#!/bin/bash
# Remove Subspace subagent integration from Codex CLI
# Removes the Subspace section from ~/.codex/AGENTS.md

set -e

AGENTS_FILE="$HOME/.codex/AGENTS.md"
MARKER="## Subspace Subagent System"

if [ ! -f "$AGENTS_FILE" ]; then
    echo "No AGENTS.md found at $AGENTS_FILE"
    exit 0
fi

if ! grep -q "$MARKER" "$AGENTS_FILE"; then
    echo "Subspace integration not found in $AGENTS_FILE"
    exit 0
fi

# Create backup
cp "$AGENTS_FILE" "$AGENTS_FILE.bak"

# Remove everything from marker to end of file (or next ## section)
# Using sed to remove from marker to EOF
sed -i '' "/$MARKER/,\$d" "$AGENTS_FILE"

# Remove trailing whitespace
sed -i '' -e :a -e '/^\s*$/d;N;ba' "$AGENTS_FILE" 2>/dev/null || true

echo "✓ Subspace integration removed from $AGENTS_FILE"
echo "  Backup saved to $AGENTS_FILE.bak"
