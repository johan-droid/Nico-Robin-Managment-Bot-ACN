#!/bin/bash
# Script to update memory.md with latest project status
# Run this periodically or after significant changes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📊 Checking project status for Nico Robin Management Bot..."

# Check git status
git status --short

echo ""
echo "📁 Current file structure:"
find backend/src -name "*.rs" | wc -l
echo "Rust source files"

echo ""
echo "📝 Memory.md last modified:"
ls -la memory.md

echo ""
echo "Memory update rules:"
echo "  - Update memory.md after every major batch / optimization."
echo "  - Check src/handlers/*.rs, src/db/*.rs, and Cargo.toml for changes."
