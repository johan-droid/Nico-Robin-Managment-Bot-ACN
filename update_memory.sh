#!/bin/bash
# Script to update memory.md with latest project status
# Run this periodically or after significant changes

echo "📊 Checking project status..."

# Check git status
cd /home/ashutosh/Downloads/Nico\ Robin\ Bot\ ACN
git status --short

echo ""
echo "📁 Current file structure:"
find backend/src -name "*.rs" | wc -l
echo "Rust source files"

echo ""
echo "📝 Memory.md last modified:"
ls -la memory.md

echo ""
echo "To update memory.md, run the subagent or manually edit the file."
echo "Key areas to check:"
echo "  - src/handlers/*.rs (command implementations)"
echo "  - src/db/*.rs (database functions)"
echo "  - migrations/*.sql (schema changes)"
echo "  - Cargo.toml (dependencies)"
