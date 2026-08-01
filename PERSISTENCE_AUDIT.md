# Nico Robin Management Bot - Persistence Audit Report

## 1. Overview
This report details the persistence requirements of every feature, command, and module in the Nico Robin Management Bot to ensure a complete redesign of the persistence layer.
The goal is zero data loss on restart, full state recovery, and automated cleanup of expired or orphaned data.

## 2. Command Audit & Database Mapping

### Moderation Commands
| Command | Purpose | Data Stored | DB Table | Columns | When Created | When Updated | When Deleted | Auto Cleanup |
|---------|---------|-------------|----------|---------|--------------|--------------|--------------|--------------|
| `/ban` | Permanent Ban | Ban record | `gbans` | `user_id`, `user_name`, `reason`, `banned_by`, `banned_at` | On `/ban` | N/A | On `/unban` | When group deleted |
| `/unban` | Remove Ban | None | `gbans` | N/A | N/A | N/A | Deletes ban record | N/A |
| `/kick` | Remove user | Audit log | `audit_logs` | `group_id`, `action`, `target_id`, `executor_id`, `reason` | On `/kick` | N/A | N/A | Log retention policy |
| `/mute` | Permanent Mute | Mute record | `mutes` | `group_id`, `user_id`, `reason`, `muted_by`, `muted_at` | On `/mute` | N/A | On `/unmute` | When group/user deleted |
| `/unmute` | Remove Mute | None | `mutes` | N/A | N/A | N/A | Deletes mute record | N/A |
| `/warn` | Issue warning | Warning record | `warnings` | `id`, `group_id`, `user_id`, `reason`, `warned_by`, `created_at` | On `/warn` | N/A | On `/resetwarn` | When group/user deleted |
| `/warns` | Check warnings | None (Read-only) | `warnings` | N/A | N/A | N/A | N/A | N/A |
| `/resetwarn` | Clear warnings | None | `warnings` | N/A | N/A | N/A | Deletes user warnings | N/A |
| `/tmute` | Temp mute | Temp mute record | `temp_mutes` | `group_id`, `user_id`, `reason`, `muted_by`, `muted_at`, `expires_at` | On `/tmute` | N/A | On `/unmute` | Expired naturally |
| `/tban` | Temp ban | Temp ban record | `temp_bans` | `group_id`, `user_id`, `reason`, `banned_by`, `banned_at`, `expires_at` | On `/tban` | N/A | On `/unban` | Expired naturally |
| `/del` | Delete message | Audit log | `audit_logs` | Same as above | On `/del` | N/A | N/A | Log retention policy |
| `/purge` | Bulk delete | Audit log | `audit_logs` | Same as above | On `/purge` | N/A | N/A | Log retention policy |
| `/pin` / `/unpin` | Manage pins | Pin state | `group_pins` | `group_id`, `message_id`, `pinned_at` | On `/pin` | N/A | On `/unpin` | When unpinned naturally |
| `/autowarnon` / `off` | Toggle autowarn | Toggle state | `auto_warn_settings`| `group_id`, `enabled`, `updated_at` | On `/autowarnon` | On toggle | When group deleted | N/A |

### Security & Anti-Spam
| Command | Purpose | Data Stored | DB Table | Columns | When Created | When Updated | When Deleted | Auto Cleanup |
|---------|---------|-------------|----------|---------|--------------|--------------|--------------|--------------|
| `/setflood` | Flood limit | Flood config | `flood_settings` | `group_id`, `flood_limit`, `flood_mode`, `flood_window_seconds`, `updated_at` | On `/setflood` | On update | When group deleted | N/A |
| `/addswear` | Add swear | Swear word | `swears` | `group_id`, `word`, `created_by`, `created_at` | On `/addswear`| N/A | On `/delswear`| When group deleted |
| `/delswear` | Remove swear| None | `swears` | N/A | N/A | N/A | Deletes swear word | N/A |
| Anti-Links / Spam | System limits | Audit logs | `audit_logs` | - | Automated | N/A | N/A | Log retention policy |

### Lock Commands
| Command | Purpose | Data Stored | DB Table | Columns | When Created | When Updated | When Deleted | Auto Cleanup |
|---------|---------|-------------|----------|---------|--------------|--------------|--------------|--------------|
| `/lock` | Lock media | Lock state | `group_locks` | `group_id`, `lock_type`, `enabled`, `toggled_by`, `toggled_at` | On `/lock` | On toggle | When group deleted | N/A |
| `/unlock` | Unlock media | Lock state | `group_locks` | Same as above | N/A | On toggle | When group deleted | N/A |

### Rules & Notes Commands
| Command | Purpose | Data Stored | DB Table | Columns | When Created | When Updated | When Deleted | Auto Cleanup |
|---------|---------|-------------|----------|---------|--------------|--------------|--------------|--------------|
| `/setrules` | Set rules | Rule text | `group_rules` | `group_id`, `rules`, `updated_by`, `updated_at` | On `/setrules`| On update | On `/clearrules`| When group deleted |
| `/clearrules` | Delete rules| None | `group_rules` | N/A | N/A | N/A | Deletes rules | N/A |
| `/save` | Save note | Note content | `notes` | `group_id`, `name`, `content`, `created_by`, `created_at` | On `/save` | On overwrite | On `/clear` | When group deleted |
| `/clear` | Delete note | None | `notes` | N/A | N/A | N/A | Deletes note | N/A |

### Feature Commands
| Command | Purpose | Data Stored | DB Table | Columns | When Created | When Updated | When Deleted | Auto Cleanup |
|---------|---------|-------------|----------|---------|--------------|--------------|--------------|--------------|
| `/enable` | Enable feature| Feature state | `feature_flags` | `group_id`, `feature_name`, `enabled`, `toggled_by`, `toggled_at` | On `/enable` | On `/disable`| When group deleted | N/A |
| `/disable` | Disable feature| Feature state | `feature_flags` | Same as above | N/A | On toggle | When group deleted | N/A |

### Configuration (Groups)
| Group Settings | Purpose | Data Stored | DB Table | Columns | When Created | When Updated | When Deleted | Auto Cleanup |
|----------------|---------|-------------|----------|---------|--------------|--------------|--------------|--------------|
| Core Settings | General cfg | Basic config | `groups` | `chat_id`, `title`, `is_active`, `language`, `timezone`, `prefix`, `created_at`, `updated_at` | Bot joins | Any update | Bot leaves | Bot kicked |

### Missing Features (To Be Implemented via Migrations)
1. **Administration:** `admin_cache`, `trusted_users`, `blacklisted_users`, `whitelists`
2. **Automation:** `scheduled_jobs`, `auto_deletes`, `timers`, `reminders`, `backup_jobs`
3. **Economy:** `economy_profiles`, `xp_history`, `daily_rewards`
4. **Games:** `game_sessions`, `quiz_questions`, `one_piece_bounties`, `daily_pairings`, `leaderboards`
5. **AI:** `ai_memory`, `ai_settings`, `prompt_overrides`, `ai_cooldowns`
6. **Logging:** `log_channels`, `audit_logs`

## 3. Database Schema Overview
The new schema involves normalizing the `groups` table and adding robust structures for all feature modules.

**Core Principles:**
- All group-related tables must use `group_id BIGINT REFERENCES groups(chat_id) ON DELETE CASCADE`.
- All temporary states (`temp_mutes`, `temp_bans`) must have `expires_at TIMESTAMPTZ NOT NULL`.
- Automatic cleanup tasks will periodically query and delete expired rows.

## 4. Current Gaps
- `temp_mutes` and `temp_bans` rely entirely on Telegram's API for duration tracking. If the bot restarts, it doesn't lose state (Telegram handles it), but if the bot needs to audit or act upon expiration (e.g. logging the unmute), it cannot.
- `mutes` aren't stored persistently in the database either; they are solely handled via Telegram restrictions.
- `groups.settings` currently uses a JSON blob.

## 5. Reverse Command Compliance
Every "set" or "enable" action must be cleaned up properly by its reverse command (`/unban`, `/unmute`, `/delswear`, `/clear`, `/clearrules`).
