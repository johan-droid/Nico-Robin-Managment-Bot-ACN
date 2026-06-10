# Command Matrix

Command bindings mapped to feature gates (`src/bot/bot/middleware/feature_gate.py` and `src/bot/services/feature_service.py`):

| Command | Feature Gate | Appears in Telegram Menu | Description |
| :--- | :--- | :--- | :--- |
| `start` | (none) | Yes | DM welcome and bot intro |
| `help` | (none) | Yes | Main help message |
| `ping` | (none) | Yes | Alive check |
| `robin` | (none) | Yes | Nico Robin quote |
| `check_handlers` | (none) | Yes | Show registered command callbacks |
| `management` | (none) | Yes | Management command guide |
| `features` | (none) | Yes | Feature status |
| `enable` | (none) | Yes | Enable feature |
| `disable` | (none) | Yes | Disable feature |
| `toggle` | (none) | Yes | Toggle feature |
| `feature_info` | (none) | Yes | Feature info |
| `feature_logs` | (none) | Yes | Feature toggle history |
| `feature_stats` | (none) | Yes | Feature usage stats |
| `my_features` | (none) | Yes | Features for role |
| `reset_features` | (none) | Yes | Reset feature settings |
| `enable_category` | (none) | Yes | Enable feature category |
| `disable_category`| (none) | Yes | Disable feature category |
| `ban` | `moderation` | Yes | Ban user |
| `unban` | `moderation` | Yes | Unban user |
| `kick` | `moderation` | Yes | Kick user |
| `mute` | `moderation` | No | Mute user |
| `unmute` | `moderation` | No | Unmute user |
| `warn` | `moderation` | No | Warn user |
| `warns` | `moderation` | No | Show user warnings |
| `resetwarn` | `moderation` | No | Reset user warnings |
| `slowmode` | `moderation` | No | Set slowmode |
| `del` | `moderation` | No | Delete message |
| `pin` | `moderation` | No | Pin message |
| `filter` | `filters` | No | Add filter |
| `stop` | `filters` | No | Stop filter |
| `filters` | `filters` | No | List filters |
| `filteraction` | `filters` | No | Set filter action |
| `setwelcome` | `welcome` | No | Set welcome text |
| `resetwelcome` | `welcome` | No | Reset welcome |
| `welcome` | `welcome` | No | Toggle welcome |
| `setwelcomedm` | `welcome` | No | Set welcome DM |
| `welcomedm` | `welcome` | No | Toggle welcome DM |
| `setfarewell` | `welcome` | No | Set farewell text |
| `farewell` | `welcome` | No | Toggle farewell |
| `cleanwelcome` | `welcome` | No | Toggle clean welcome |
| `welcometest` | `welcome` | No | Test welcome |
| `save` | `notes` | No | Save note |
| `get` | `notes` | No | Get note |
| `notes` | `notes` | No | List notes |
| `clear` | `notes` | No | Clear note |
| `purge` | `purge` | No | Purge messages |
| `schedule` | `scheduler` | No | Schedule message |
| `captcha` | `captcha` | No | Trigger captcha |
| `newfed` | `federation` | No | Create fed |
| `joinfed` | `federation` | No | Join fed |
| `addbroadcast` | `acn_broadcast`| No | Add broadcast channel |
| `removebroadcast` | `acn_broadcast`| No | Remove broadcast channel |
| `broadcastchannels`| `acn_broadcast`| Yes | List broadcast channels |
| `broadcaststatus` | `acn_broadcast`| Yes | Broadcast status |
| `broadcasthelp` | `acn_broadcast`| Yes | Broadcast help |
| `testbroadcast` | `acn_broadcast`| Yes | Test broadcast |
| `flirt` | `flirting` | No | Flirt |
| `flirt_stats` | `flirting` | No | Flirt stats |
| `flirt_categories`| `flirting` | No | Flirt categories |
| `flirt_achievements`| `flirting` | No | Flirt achievements |
| `flirt_example` | `flirting` | No | Flirt example |
| `points` | `points` | No | View points |
| `leaderboard` | `points` | Yes | Points leaderboard |
| `apploids` | `points` | Yes | Show apploids |
| `buy_apploid` | `points` | Yes | Buy apploid |
| `equip_apploid` | `points` | Yes | Equip apploid |
| `point_stats` | `points` | Yes | Point stats |
| `earn_points` | `points` | Yes | Earn points |
| `point_help` | `points` | Yes | Point help |
| `profile` | `profile` | Yes | Member profile |
| `setbio` | `profile` | Yes | Set bio |
| `toggleai` | `security` | No | Toggle AI mod |
| `setflood` | `security` | No | Set flood limit |
| `setfloodmode` | `security` | No | Set flood mode |
| `flood` | `security` | No | Toggle flood control |
| `addswear` | `security` | Yes | Add swear word |
| `delswear` | `security` | Yes | Delete swear word |
| `swearlist` | `security` | Yes | List swear words |
| `swearsettings` | `security` | Yes | Swear settings |
| `export_my_data` | `profile` | No | Export data |
| `delete_my_data` | `profile` | No | Delete data |
| `clear_user_data` | `security` | No | Clear user data |

Notes:
* Features like `toggleai`, `flood`, `addswear` map to `security` since it protects the chat.
