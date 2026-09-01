---
name: memory-vault-update
description: Protocol for updating the project Obsidian memory vault (memory.md) after every progress batch, code change, or architecture update so the AI agent never forgets progress or context.
---

# Memory Vault Update Skill (MCL)

## Purpose
This skill ensures that after every progress batch, code modification, database migration, or architectural update, the AI agent automatically updates `memory.md` (the Obsidian memory vault) and `FREE_TIER_NEON_STRUCTURE.md`.

## Protocol Steps for Agent Execution

1. **Inspect Recent Changes**:
   - Check modified files in `backend/src/` and configuration files (`Cargo.toml`, `.env.example`, `.env.local`).
   - Review database schema changes or new migrations in `backend/migrations/`.

2. **Update `memory.md` Vault**:
   - Update **Last Updated** timestamp to current date.
   - Update **Current Status & Progress Milestones** with completed batch items.
   - Update **Database & Caching Architecture** table if cache TTLs, write guards, or DB queries were modified.
   - Append to **Progress Log / Batch History** describing the batch summary.

3. **Verify Documentation Consistency**:
   - Verify that [FREE_TIER_NEON_STRUCTURE.md](file:///home/ashutoshsahoo/Downloads/Nico%20Robin%20Managment%20Bot/Nico-Robin-Managment-Bot-ACN/FREE_TIER_NEON_STRUCTURE.md) aligns with settings (`PERSIST_MESSAGE_HISTORY`, `ENABLE_COMMAND_LOGGING`, `DB_POOL_SIZE`, `CACHE_TTL_SECS`).
   - Run `./update_memory.sh` to confirm project structure sanity.

4. **Persist Progress**:
   - Ensure all learnings and constraints (e.g. Neon 100 hr compute limit, Heroku 512 MB RAM limit) are preserved across conversation turns.
