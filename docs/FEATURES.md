# Nico Robin Bot - Features Guide

## 🌸 What Nico Robin Bot Does

Nico Robin Bot is a Telegram group management bot for moderation, community utilities, and ACN-specific social systems. It helps admins run a group with tools for rules enforcement, welcome flows, notes, stats, and optional feature controls.

It also includes ACN-only systems for loyalty, points, broadcasts, bot friendship, and flirting.

---

## 🛡️ Moderation And Protection

These commands help admins keep chats orderly and consistent.

- `/toggleai on/off` - enable or disable AI moderation features
- `/ban` - ban a user
- `/unban` - remove a ban
- `/kick` - remove a user from the group
- `/mute` - prevent a user from sending messages
- `/unmute` - restore speaking access
- `/warn [reason]` - issue a warning
- `/warns` - show warning count
- `/resetwarn` - clear warnings
- `/slowmode [seconds]` - set message rate limiting

Content cleanup commands:

- `/del` - delete the replied-to message
- `/purge` - delete multiple messages
- `/pin` - pin a message
- `/filter [word]` - add a word or phrase filter
- `/stop [word]` - remove a filter
- `/filters` - list active filters
- `/filteraction [action]` - set the action used when a filter triggers

---

## 👋 Welcome, Farewell, And Rules

These commands manage onboarding and group guidance.

- `/setwelcome [message]` - set the welcome message
- `/resetwelcome` - clear the custom welcome message
- `/welcome on/off` - toggle welcome messages
- `/setfarewell [message]` - set the farewell message
- `/farewell on/off` - toggle farewell messages
- `/cleanwelcome on/off` - toggle welcome cleanup
- `/welcometest` - preview the current welcome message
- `/setrules [text]` - set group rules
- `/rules` - show group rules

---

## 📊 Group Info And Notes

- `/stats` - show group statistics
- `/id` - show your user ID or the chat ID
- `/whois` - inspect a user
- `/info` - alias for `/whois`
- `/save [name] [text]` - save a note
- `/get [name]` - retrieve a note
- `/notes` - list saved notes
- `/clear [name]` - delete a saved note
- `#notename` - quick access to a note

---

## ⚙️ Settings And Safety Controls

- `/setlocale [language]` - change the group language
- `/setwarnlimit [number]` - set warnings before escalation
- `/setwarnaction [action]` - choose the escalation action
- `/setflood [number]` - set flood threshold
- `/setfloodmode [mode]` - set flood punishment mode
- `/flood on/off` - enable or disable flood control
- `/captcha on/off` - enable or disable new member verification

---

## 🔧 Feature Management

Feature management is for groups that want to switch modules on or off without touching code.

- `/features` - view feature status
- `/my_features` - view features available to your role
- `/feature_info <feature>` - inspect one feature
- `/feature_logs [feature]` - view change history
- `/feature_stats [feature]` - view usage statistics
- `/enable <feature>` - enable a feature
- `/disable <feature>` - disable a feature
- `/toggle <feature>` - toggle a feature
- `/enable_category <category>` - enable a feature category
- `/disable_category <category>` - disable a feature category
- `/reset_features confirm` - reset feature settings

These commands are restricted to ACN leadership roles where the bot enforces it.

---

## 🤝 Federation

- `/newfed [name]` - create a federation
- `/joinfed [fed_id]` - join a federation

Federation actions are group-controlled and owner or admin restricted where required.

---

## ⏰ Scheduling

- `/schedule [time] [message]` - schedule an announcement

---

## ⚓ ACN Loyalty And Access

These features are for Anime Crew Network groups and members.

- `/acn_status` - show your ACN role, rank, and loyalty points
- `/loyalty_leaderboard` - show the ACN leaderboard
- `/acn_info` - show ACN group statistics
- `/acn_members` - list ACN members in the group
- `/addacngroup` - whitelist the current group as an ACN group
- `/addacn <user_id> <role>` - add an ACN member
- `/removeacn <user_id>` - remove an ACN member
- `/award <user_id> <points> [reason]` - award loyalty points

The available ACN roles are captain, commander, member, and ally.

`/addacn` currently accepts a numeric user ID. The code does not resolve usernames yet.

---

## 📡 ACN Broadcast System

- `/broadcastchannels` - list configured broadcast channels
- `/broadcaststatus` - show broadcast status
- `/testbroadcast [message]` - send a test broadcast
- `/broadcasthelp` - show broadcast help
- `/addbroadcast <channel_id> <type> [name]` - add a broadcast channel
- `/removebroadcast <channel_id>` - remove a broadcast channel
- `/addmaingroup` - mark the current group as a main broadcast group

The bot also supports channel delivery helpers that are currently registered in the command menu:

- `/channelpost` - send a message to a channel
- `/channelphoto` - send a photo to a channel

---

## 🧭 Channel Guard

These commands manage channel-level guard and purge routing.

- `/addpurgechannel <channel_id> [name]` - add a purge channel
- `/removepurgechannel <channel_id>` - remove a purge channel
- `/purgechannels` - list configured purge channels

---

## 🌙 Night Mode And Logs

- `/nightmode [on|off]` - toggle the group night mode state
- `/setlogchannel <channel_id>` - set the group log channel
- `/removelogchannel` - clear the group log channel

---

## 👤 Profiles

- `/profile` - show a member profile
- `/setbio [text]` - set your profile bio

---

## 🧪 Swear Words

- `/addswear <word> [severity] [punishment] [duration]` - add a swear-word rule
- `/delswear <word>` - remove a swear-word rule
- `/swearlist` - list configured swear words
- `/swearsettings [severity] [punishment] [duration]` - set default swear-word behavior

---

## 💫 ACN Points And Apploids

- `/points` - show your point balance and level
- `/leaderboard [limit]` - show the point leaderboard
- `/apploids` - view owned and available apploids
- `/buy_apploid <name>` - buy an apploid
- `/equip_apploid <name>` - equip an apploid
- `/point_stats` - show group point statistics
- `/earn_points` - explain how to earn points
- `/point_help` - show point system help

Points, levels, and apploids are ACN-only and are tracked per group.

---

## 💕 Yamato Friendship System

- `/bond_with_yamato` - start the friendship in the current group
- `/yamato_interact <type>` - trigger a friendship interaction
- `/yamato_status` - show friendship status
- `/yamato_memories` - view shared memories
- `/gift_to_yamato <type> <message>` - send a virtual gift
- `/yamato_activities` - show recent friendship activity
- `/yamato_help` - show friendship help

Available interaction types are `waifu`, `compliment`, `moment`, `tease`, and `deep`.

Available gift types are `flower`, `book`, `sword`, `heart`, `star`, and `treasure`.

---

## 🌸 Nico Robin Flirting

- `/flirt <message>` - try a flirt attempt
- `/flirt_stats` - view your flirting statistics
- `/flirt_categories` - list flirting categories
- `/flirt_achievements` - show earned achievements
- `/flirt_help` - show flirting help
- `/flirt_example` - show example flirt lines
- `/flirt_random` - generate a random flirt line

The flirting system currently uses these categories: charming, intellectual, mysterious, playful, romantic, and confident.

---

## 🎭 Nico Robin Moments

- `/pat` - Robin pats someone
- `/slap` - Robin gives a reality check
- `/hug` - Robin gives a warm hug
- `/robin_smile` - show Robin smiling
- `/robin_blush` - show Robin blushing
- `/robin_angry` - show Robin’s serious side
- `/robin_confused` - show Robin confused
- `/robin_dance` - show Robin dancing
- `/robin_sleep` - show Robin sleeping
- `/robin_moments` - list the moment commands

---

## 🎉 Fun And Utility

- `/ping` - check whether the bot is online
- `/robin` - get a random Robin quote

---

## 🛟 Support Commands

- `/start` - show the DM welcome and bot intro
- `/help` - show the main help message
- `/management` - show the moderation and settings guide

---

## 🚀 Getting Started

1. Add Nico Robin Bot to your Telegram group.
2. Grant the bot the admin permissions it needs for moderation.
3. Turn on the features you want, starting with `/toggleai on` if you want moderation enabled.
4. Configure welcome, filters, points, or ACN features as needed.
5. Use `/help` or `/management` in chat to review the command guides.

---

## 📞 Need Help?

- Use `/help` for the general command guide.
- Use `/management` for moderation and settings commands.
- Use each feature’s dedicated help command for deeper usage.

Nico Robin Bot helps keep Telegram groups organized, expressive, and easier to manage. 🌸
