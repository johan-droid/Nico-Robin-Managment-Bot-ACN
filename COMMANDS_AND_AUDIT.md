# 🤖 Nico Robin Bot — Comprehensive Command Reference & Usage Guide

> **Project:** Nico Robin Management Bot (ACN)  
> **Stack:** Rust · Axum · Tokio · PostgreSQL (Neon) · Telegram Bot API  
> **Last Updated:** 2026-08-01  

---

## 📑 Table of Contents

1. [Permission Levels](#-permission-levels)
2. [Core Commands](#-core-commands)
3. [Profile Commands](#-profile-commands)
4. [Notes Commands](#-notes-commands)
5. [Filter Commands](#-filter-commands)
6. [Welcome & Farewell Commands](#-welcome--farewell-commands)
7. [Security Commands](#-security-commands)
8. [Moderation Commands](#-moderation-commands)
9. [Lock Commands](#-lock-commands)
10. [Rules Commands](#-rules-commands)
11. [Feature Toggle Commands](#-feature-toggle-commands)
12. [Federation Commands](#-federation-commands)
13. [Fun Commands](#-fun-commands)

---

## 🔑 Permission Levels

| Level | Symbol | Who | Description |
|-------|--------|-----|-------------|
| **Everyone** | 🌍 | Any chat member | Open access — no special permissions required. |
| **Admin** | 🛡️ | Group admins & Sudo users | Requires Telegram admin privileges in the current chat. |
| **Sudo / Captain** | 👑 | Bot Owners & Group Creator | Bot super-administrators and group owners. |

---

## 🏠 Core Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/start` | `/start` | **Greeting** | 🌍 Everyone | **Explanation**: Initializes bot interaction, registers user state, and displays the main interactive home card.<br>**How to use**: Send `/start` in a private message (DM) to open the main menu with action buttons (`➕ Add to group`, `❓ Help`, `ℹ️ About`). |
| `/help` | `/help` | **Reference** | 🌍 Everyone | **Explanation**: Opens the interactive command guide catalog structured into moderator and member categories.<br>**How to use**: Send `/help` in any chat, then select a category button (`🛡️ Moderator Commands` or `👤 Non-Moderator Commands`) to view commands. |

---

## 👤 Profile Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/profile` | `/profile [@user]` or reply | **Card** | 🌍 Everyone | **Explanation**: Fetches and renders a complete profile card showing profile photo, full name, username, Telegram ID, group role, join date, and custom bio.<br>**How to use**: Send `/profile` for yourself, OR reply to any member's message with `/profile`, OR type `/profile @username` / `/profile 123456789`. |
| `/setbio` | `/setbio <text>` | **Biography** | 🌍 Everyone | **Explanation**: Stores a custom personal biography in the database linked to your account, displayed on your profile card.<br>**How to use**: Send `/setbio Hello! I am a software engineer and group co-host.` to update your bio. |
| `/exportmydata` | `/exportmydata` | **Export** | 🌍 Everyone | **Explanation**: Generates and sends a complete JSON dump of all personal data stored about your account in the bot database.<br>**How to use**: Send `/exportmydata` in DM with the bot to receive your JSON data file. |
| `/deletemydata` | `/deletemydata` | **Erasure** | 👑 Captain/Dev | **Explanation**: Permanently wipes and deletes all database records associated with your account from the bot database.<br>**How to use**: Send `/deletemydata` in DM with the bot to erase all saved profile data. |
| `/staff` | `/staff` | **Roster** | 🌍 Everyone | **Explanation**: Scans the group administration hierarchy and lists all group owners, co-founders, and active admins.<br>**How to use**: Send `/staff` in any group chat to display the staff roster. |

---

## 📝 Notes Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/save` | `/save <keyword> <content>` or reply | **Store** | 🛡️ Admin | **Explanation**: Saves text, links, or media under a specific keyword trigger scoped to the current group.<br>**How to use**: Direct: Send `/save rules Please follow guidelines.`; Reply: Reply to an important message with `/save faq` to save it under keyword `faq`. |
| `/get` | `/get <keyword>` or `#keyword` | **Retrieve** | 🌍 Everyone | **Explanation**: Looks up and posts the saved content associated with a note keyword.<br>**How to use**: Send `/get rules` OR simply type `#rules` anywhere in the group text. |
| `/notes` | `/notes` | **Catalog** | 🌍 Everyone | **Explanation**: Lists all saved note keywords stored in the current group database.<br>**How to use**: Send `/notes` in the group chat to view all available note keywords. |
| `/clear` | `/clear <keyword>` | **Remove** | 🛡️ Admin | **Explanation**: Deletes a specific saved note from the group database by its keyword.<br>**How to use**: Send `/clear rules` to delete the note saved under `rules`. |

---

## 🔍 Filter Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/filter` | `/filter <trigger> <response>` | **Auto-reply** | 🛡️ Admin | **Explanation**: Creates an automated trigger-and-response rule. Whenever any member sends a message containing `<trigger>`, the bot responds with `<response>`.<br>**How to use**: Send `/filter website https://example.com` to auto-reply with the link whenever "website" is mentioned. |
| `/stop` | `/stop <trigger>` | **Delete** | 🛡️ Admin | **Explanation**: Deletes an automated auto-reply filter trigger from the group.<br>**How to use**: Send `/stop website` to stop auto-replying when "website" is typed. |
| `/filters` | `/filters` | **Overview** | 🌍 Everyone | **Explanation**: Lists all active trigger-and-response auto-reply rules configured in the group.<br>**How to use**: Send `/filters` to view all active auto-reply keywords and responses. |

---

## 👋 Welcome & Farewell Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/setwelcome` | `/setwelcome <message>` | **Welcome** | 🛡️ Admin | **Explanation**: Sets the custom greeting posted when a new member joins (`{user}` = name, `{group}` = title, `{count}` = total members).<br>**How to use**: Send `/setwelcome Welcome {user} to {group}! You are member #{count}.` |
| `/resetwelcome` | `/resetwelcome` | **Reset** | 🛡️ Admin | **Explanation**: Clears the custom welcome message and restores default bot greeting.<br>**How to use**: Send `/resetwelcome` in the group chat. |
| `/welcome` | `/welcome` | **Preview** | 🛡️ Admin | **Explanation**: Renders a live preview of the active welcome greeting message.<br>**How to use**: Send `/welcome` in the group chat. |
| `/setwelcomedm` | `/setwelcomedm <message>` | **Direct-message** | 🛡️ Admin | **Explanation**: Configures a private welcome message sent directly to a new member's DM upon joining.<br>**How to use**: Send `/setwelcomedm Thanks for joining {group}! Please read our rules.` |
| `/setfarewell` | `/setfarewell <message>` | **Farewell** | 🛡️ Admin | **Explanation**: Sets the goodbye message posted when a member leaves (`{user}`, `{group}`).<br>**How to use**: Send `/setfarewell Goodbye {user}, hope to see you again in {group}!` |
| `/farewell` | `/farewell` | **Preview** | 🛡️ Admin | **Explanation**: Displays a live preview of the configured farewell message.<br>**How to use**: Send `/farewell` in the group chat. |
| `/cleanwelcome` | `/cleanwelcome` | **Auto-delete** | 🛡️ Admin | **Explanation**: Toggles automatic deletion of welcome messages after 60 seconds to prevent chat clutter.<br>**How to use**: Send `/cleanwelcome` to turn auto-cleaning ON or OFF. |
| `/welcometest` | `/welcometest` | **Test** | 🛡️ Admin | **Explanation**: Simulates a join event using your username and member count to test formatting.<br>**How to use**: Send `/welcometest` in the group chat. |

---

## 🔒 Security Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/setflood` | `/setflood <count>` | **Limit** | 🛡️ Admin | **Explanation**: Sets maximum allowed messages per user in 10 seconds (`0` disables anti-flood). Exceeding triggers warning or mute.<br>**How to use**: Send `/setflood 5` to set a limit of 5 messages per 10 seconds. |
| `/flood` | `/flood` | **Status** | 🛡️ Admin | **Explanation**: Displays current anti-flood security settings including limit and action mode.<br>**How to use**: Send `/flood` in the group chat. |
| `/addswear` | `/addswear <word>` | **Block** | 🛡️ Admin | **Explanation**: Adds a word to the bad word blacklist. Matching messages are deleted and warned.<br>**How to use**: Send `/addswear badword` to block "badword". |
| `/delswear` | `/delswear <word>` | **Unblock** | 🛡️ Admin | **Explanation**: Removes a word from the bad word blacklist.<br>**How to use**: Send `/delswear badword` to unblock "badword". |
| `/report` | `/report` (reply) or `@admin` | **Flag** | 🌍 Everyone | **Explanation**: Flags an inappropriate message directly to all admins and logs it to the log channel.<br>**How to use**: Reply to any spam or offensive message with `/report`. |

---

## 🔨 Moderation Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/ban` | `/ban @user [reason]` or reply | **Ban** | 🛡️ Admin | **Explanation**: Permanently bans a user from the group and deletes recent activity.<br>**How to use**: Reply to a message with `/ban Spamming` OR send `/ban @spammer Excessive ads`. |
| `/unban` | `/unban @user` or reply | **Unban** | 🛡️ Admin | **Explanation**: Revokes a ban so the user can rejoin via invite link.<br>**How to use**: Send `/unban @user123` or reply to their message with `/unban`. |
| `/kick` | `/kick @user [reason]` or reply | **Remove** | 🛡️ Admin | **Explanation**: Removes a user from the group without a permanent ban (they can rejoin via link).<br>**How to use**: Reply to a message with `/kick Please read the rules`. |
| `/mute` | `/mute @user [reason]` or reply | **Mute** | 🛡️ Admin | **Explanation**: Restricts a user's permission to send text, media, or links in the group.<br>**How to use**: Reply to a message with `/mute Disruption in chat`. |
| `/unmute` | `/unmute @user` or reply | **Unmute** | 🛡️ Admin | **Explanation**: Restores full chat messaging permissions to a muted user.<br>**How to use**: Send `/unmute @user123` or reply to their message with `/unmute`. |
| `/warn` | `/warn @user [reason]` or reply | **Warning** | 🛡️ Admin | **Explanation**: Issues an official warning to a user. Upon reaching 3 warnings, the user is auto-banned.<br>**How to use**: Reply to a rule violation with `/warn Inappropriate language`. |
| `/warns` | `/warns @user` or reply | **Inspection** | 🛡️ Admin | **Explanation**: Displays a user's total warning count and detailed reasons.<br>**How to use**: Reply to a user's message with `/warns` or send `/warns @user`. |
| `/resetwarn` | `/resetwarn @user` or reply | **Clear** | 🛡️ Admin | **Explanation**: Clears all warning records for a user, resetting count back to 0.<br>**How to use**: Reply to a user's message with `/resetwarn` or send `/resetwarn @user`. |
| `/slowmode` | `/slowmode <sec>` | **Delay** | 🛡️ Admin | **Explanation**: Sets required wait time (seconds) between messages for non-admin members (`0` disables).<br>**How to use**: Send `/slowmode 15` to require a 15-second wait between messages. |
| `/del` | `/del` (reply) | **Delete** | 🛡️ Admin | **Explanation**: Immediately deletes the replied-to message and the `/del` command call.<br>**How to use**: Reply to any unwanted message with `/del`. |
| `/purge` | `/purge <count>` or reply | **Clean** | 🛡️ Admin | **Explanation**: Bulk deletes messages. Replying deletes target message and everything after; number deletes last N.<br>**How to use**: Reply to start message with `/purge` OR send `/purge 20` for last 20. |
| `/tmute` | `/tmute @user <duration>` | **Temporary-mute** | 🛡️ Admin | **Explanation**: Temporarily mutes a user for a duration (`30m` = 30 min, `2h` = 2 hrs, `1d` = 1 day).<br>**How to use**: Reply to a message with `/tmute 2h` to silence for 2 hours. |
| `/tban` | `/tban @user <duration>` | **Temporary-ban** | 🛡️ Admin | **Explanation**: Temporarily bans a user for a duration (`1h`, `1d`, `1w`). Automatically unbans on expiration.<br>**How to use**: Send `/tban @user 1d` to ban for 1 day. |
| `/kickme` | `/kickme` | **Self-remove** | 🌍 Everyone | **Explanation**: Removes yourself from the current group chat.<br>**How to use**: Send `/kickme` in the group chat. |
| `/pin` | `/pin` (reply) | **Highlight** | 🛡️ Admin | **Explanation**: Pins the replied-to message to the group chat header banner.<br>**How to use**: Reply to an announcement message with `/pin`. |
| `/unpin` | `/unpin` (reply) or `/unpin all` | **Unhighlight** | 🛡️ Admin | **Explanation**: Unpins a specific pinned message or clears all pinned messages.<br>**How to use**: Send `/unpin all` to clear all pinned messages. |
| `/autowarnon` | `/autowarnon` | **Enable** | 🛡️ Admin | **Explanation**: Enables automatic warning issuance for repeat spam offenders.<br>**How to use**: Send `/autowarnon` in the group chat. |
| `/autowarnoff` | `/autowarnoff` | **Disable** | 🛡️ Admin | **Explanation**: Disables automatic warning issuance.<br>**How to use**: Send `/autowarnoff` in the group chat. |

---

## 🔐 Lock Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/lock` | `/lock <type>` | **Lock** | 🛡️ Admin | **Explanation**: Restricts specific content types (`photos`, `videos`, `stickers`, `gifs`, `documents`, `voice`, `audio`, `links`, `forward`, `bots`, `polls`, `video_notes`). Matching non-admin posts are auto-deleted.<br>**How to use**: Send `/lock links` to block links, or `/lock stickers` to block stickers. |
| `/unlock` | `/unlock <type>` | **Unlock** | 🛡️ Admin | **Explanation**: Unlocks a previously restricted content type.<br>**How to use**: Send `/unlock links` to permit links again. |
| `/locks` | `/locks` | **Audit** | 🌍 Everyone | **Explanation**: Displays all currently enforced content locks in the group.<br>**How to use**: Send `/locks` in the group chat. |

---

## 📜 Rules Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/setrules` | `/setrules <text>` | **Rules** | 🛡️ Admin | **Explanation**: Saves the official group rules document in the database.<br>**How to use**: Send `/setrules 1. Be respectful\n2. No spam\n3. No self-promo`. |
| `/rules` | `/rules` | **Display** | 🌍 Everyone | **Explanation**: Displays the official group rules document.<br>**How to use**: Send `/rules` in any group chat. |
| `/clearrules` | `/clearrules` | **Erase** | 🛡️ Admin | **Explanation**: Deletes the saved group rules document.<br>**How to use**: Send `/clearrules` in the group chat. |

---

## ⚙️ Feature Toggle Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/features` | `/features` | **List** | 🌍 Everyone | **Explanation**: Displays feature override status (ON/OFF) for the chat.<br>**How to use**: Send `/features` in the group chat. |
| `/enable` | `/enable <feature>` | **Enable** | 🛡️ Admin | **Explanation**: Activates a specific feature module (`filters`, `notes`, `locks`, `welcome`, `security`, `moderation`, `rules`, `profile`, `federation`).<br>**How to use**: Send `/enable filters` to activate auto-replies. |
| `/disable` | `/disable <feature>` | **Disable** | 🛡️ Admin | **Explanation**: Deactivates a feature module for the group.<br>**How to use**: Send `/disable locks` to turn off content locking. |
| `/toggle` | `/toggle <feature>` | **Switch** | 🛡️ Admin | **Explanation**: Flips a feature state between enabled and disabled.<br>**How to use**: Send `/toggle welcome`. |
| `/enablecategory` | `/enablecategory <cat>` | **Enable-category** | 🛡️ Admin | **Explanation**: Enables every feature inside a category at once.<br>**How to use**: Send `/enablecategory moderation`. |
| `/disablecategory` | `/disablecategory <cat>` | **Disable-category** | 🛡️ Admin | **Explanation**: Disables every feature inside a category at once.<br>**How to use**: Send `/disablecategory fun`. |
| `/featureinfo` | `/featureinfo` | **Guide** | 🌍 Everyone | **Explanation**: Displays category-to-feature mapping details.<br>**How to use**: Send `/featureinfo` in the group chat. |
| `/myfeatures` | `/myfeatures` | **Summary** | 🌍 Everyone | **Explanation**: Displays summary counts of enabled vs disabled features.<br>**How to use**: Send `/myfeatures` in the group chat. |
| `/resetfeatures` | `/resetfeatures` | **Restore** | 🛡️ Admin | **Explanation**: Resets all feature overrides to default (all enabled).<br>**How to use**: Send `/resetfeatures` in the group chat. |

---

## 🌐 Federation Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/newfed` | `/newfed <name>` | **Create** | 🛡️ Admin | **Explanation**: Initializes a new multi-group federation under `<name>` and generates an 8-character ID.<br>**How to use**: Send `/newfed Anime Alliance` to create a federation. |
| `/joinfed` | `/joinfed <fed_id>` | **Connect** | 🛡️ Admin | **Explanation**: Connects the current group to an existing federation by its 8-character ID.<br>**How to use**: Send `/joinfed a1b2c3d4` to link your group. |
| `/gban` | `/gban @user <reason>` | **Global-ban** | 👑 Sudo | **Explanation**: Bans a user globally across all groups managed by the bot.<br>**How to use**: Send `/gban @spammer Raid bot`. |
| `/ungban` | `/ungban @user` | **Global-unban** | 👑 Sudo | **Explanation**: Removes a user from the global ban list.<br>**How to use**: Send `/ungban @user123`. |
| `/gbans` | `/gbans` | **Global-list** | 👑 Sudo | **Explanation**: Displays all users on the global ban list.<br>**How to use**: Send `/gbans` in the chat. |

---

## 🎨 Fun Commands

| Command | Syntax | Action Concept | Permission | Detailed Explanation & How to Use It |
|---------|--------|----------------|------------|--------------------------------------|
| `/q` | `/q [n]` (reply) | **Quote** | 🌍 Everyone | **Explanation**: Renders a replied-to message (or last N messages) into a styled image quote card with avatar and text formatting.<br>**How to use**: Reply to a message with `/q` OR reply with `/q 2` / `/q 3`. |
