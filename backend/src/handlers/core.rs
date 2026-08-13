use crate::telegram::api::Bot;
use crate::telegram::update::{CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message};
use crate::telegram::ParseMode;
use tokio_postgres::Client;

fn _btn(text: &str, cb: &str) -> InlineKeyboardButton {
    InlineKeyboardButton {
        text: text.into(),
        callback_data: Some(cb.into()),
        url: None,
    }
}

fn _url_btn(text: &str, url: &str) -> InlineKeyboardButton {
    InlineKeyboardButton {
        text: text.into(),
        callback_data: None,
        url: Some(url.into()),
    }
}

fn get_bot_username() -> String {
    if let Some(un) = crate::telegram::get_bot_username() {
        if !un.is_empty() {
            return un;
        }
    }
    std::env::var("BOT_USERNAME")
        .unwrap_or_else(|_| {
            std::env::var("BOT_NAME").unwrap_or_else(|_| "nico_robin_bot".to_string())
        })
        .trim()
        .trim_start_matches('@')
        .replace(' ', "_")
        .to_lowercase()
}

fn start_text(mention: &str) -> String {
    format!(
        concat!(
            "🌸 Hey There... {mention}\n\n",
            "✿ ∘ ━━━━━━━━┉┅╍\n",
            "<blockquote>",
            "My name is 𝗡𝗜𝗖𝗢 𝗥𝗢𝗕𝗜𝗡, and I'm a group management &amp; ",
            "moderation assistant. I'm here to keep your community organised, ",
            "secure, and effortlessly under control... quietly, of course.\n\n",
            "Oh, and yes... Poneglyphs?\n",
            "Let's just say I have a habit of uncovering things others ",
            "overlook. After all... \n",
            "\"History is not erased by silence.\" 📖",
            "</blockquote>\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "📜 Smart moderation &amp; administration tools\n",
            "🛡️ Anti-spam, protection, and automation features\n",
            "📊 Elegant controls to keep your group running smoothly\n\n",
            "Use /help to discover everything I can do. ✨",
        ),
        mention = mention,
    )
}

fn start_keyboard() -> InlineKeyboardMarkup {
    let bot_username = get_bot_username();
    let bot_name = std::env::var("BOT_NAME").unwrap_or_else(|_| "Nico Robin".to_string());
    InlineKeyboardMarkup {
        inline_keyboard: vec![
            vec![_url_btn(
                &format!("➕ Add {} to your group", bot_name),
                &format!("https://t.me/{}?startgroup=true", bot_username),
            )],
            vec![_btn("❓ Help", "help"), _btn("ℹ️ About", "about")],
        ],
    }
}

const MODERATOR_CATEGORIES: &[(&str, &str)] = &[
    ("⚔️ Moderation", "cat_moderation"),
    ("🔒 Security", "cat_security"),
    ("⭐ Features", "cat_features"),
    ("🌐 Federation", "cat_federation"),
    ("📜 Rules", "cat_rules"),
    ("🔐 Locks", "cat_locks"),
];

const NON_MODERATOR_CATEGORIES: &[(&str, &str)] = &[
    ("🌸 Profile", "cat_profile"),
    ("📝 Notes", "cat_notes"),
    ("🔍 Filters", "cat_filters"),
    ("👋 Welcome", "cat_welcome"),
    ("🎨 Fun", "cat_fun"),
];

fn help_text() -> &'static str {
    concat!(
        "📖 <b>Nico Robin Bot — Commands</b>\n\n",
        "🛡️ <b>Moderator Commands</b> — admin &amp; management tools\n",
        "👤 <b>Non-Moderator Commands</b> — commands for everyone\n\n",
        "Tap a category to see its commands:",
    )
}

fn moderator_text() -> &'static str {
    concat!(
        "🛡️ <b>Moderator Commands</b> 🛡️\n\n",
        "Admin &amp; management tools. Tap a category to see its commands:",
    )
}

fn non_moderator_text() -> &'static str {
    concat!(
        "👤 <b>Non-Moderator Commands</b> 👤\n\n",
        "Commands available to everyone. Tap a category to see its commands:",
    )
}

fn about_text() -> String {
    let bot_name = std::env::var("BOT_NAME").unwrap_or_else(|_| "Nico Robin".to_string());
    format!(
        concat!(
            "🌸 <b>About {}</b> 🌸\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "<blockquote>",
            "I am a group management &amp; moderation assistant, ",
            "built to keep your community organised, secure, ",
            "and effortlessly under control.\n\n",
            "Whether it's taming spam, managing members, ",
            "or just keeping the peace — I've got it covered. ",
            "Quietly. Elegantly. Just like the Devil Child herself.",
            "</blockquote>\n\n",
            "🛠 <b>Capabilities</b>\n",
            "• Smart moderation &amp; administration\n",
            "• Anti-spam, flood &amp; rate-limit protection\n",
            "• Custom auto-replies (filters)\n",
            "• Welcome / farewell messages\n",
            "• Notes &amp; user profiles\n",
            "• Federation support\n",
            "• Feature toggles per group\n\n",
            "Use /help to explore all commands. ✨",
        ),
        bot_name,
    )
}

fn help_keyboard() -> InlineKeyboardMarkup {
    InlineKeyboardMarkup {
        inline_keyboard: vec![
            vec![_btn("🛡️ Moderator Commands", "moderator")],
            vec![_btn("👤 Non-Moderator Commands", "nonmoderator")],
            vec![_btn("🔙 Back", "back_start")],
        ],
    }
}

fn category_keyboard(categories: &[(&str, &str)], back_cb: &str) -> InlineKeyboardMarkup {
    let mut rows: Vec<Vec<InlineKeyboardButton>> = categories
        .chunks(2)
        .map(|chunk| chunk.iter().map(|(label, cb)| _btn(label, cb)).collect())
        .collect();
    rows.push(vec![_btn("🔙 Back", back_cb)]);
    InlineKeyboardMarkup {
        inline_keyboard: rows,
    }
}

fn moderator_keyboard() -> InlineKeyboardMarkup {
    category_keyboard(MODERATOR_CATEGORIES, "back_help")
}

fn non_moderator_keyboard() -> InlineKeyboardMarkup {
    category_keyboard(NON_MODERATOR_CATEGORIES, "back_help")
}

fn category_back_keyboard(back_cb: &str) -> InlineKeyboardMarkup {
    InlineKeyboardMarkup {
        inline_keyboard: vec![vec![_btn("🔙 Back", back_cb)]],
    }
}

fn is_moderator_category(cb: &str) -> bool {
    MODERATOR_CATEGORIES.iter().any(|(_, c)| *c == cb)
}

fn is_non_moderator_category(cb: &str) -> bool {
    NON_MODERATOR_CATEGORIES.iter().any(|(_, c)| *c == cb)
}

/// Resolve a callback payload into the page (text + keyboard) to render.
/// `mention` is only used when navigating back to the `/start` page.
fn page_for(data: &str, mention: &str) -> (String, InlineKeyboardMarkup) {
    match data {
        "help" => (help_text().to_string(), help_keyboard()),
        "moderator" | "back_moderator" => (moderator_text().to_string(), moderator_keyboard()),
        "nonmoderator" | "back_nonmoderator" => {
            (non_moderator_text().to_string(), non_moderator_keyboard())
        }
        "about" => (about_text(), category_back_keyboard("back_start")),
        "back_start" => (start_text(mention), start_keyboard()),
        "back_help" => (help_text().to_string(), help_keyboard()),
        _ if data == "cat_game" => (
            category_text(data).to_string(),
            category_back_keyboard("back_help"),
        ),
        _ if is_moderator_category(data) => (
            category_text(data).to_string(),
            category_back_keyboard("back_moderator"),
        ),
        _ if is_non_moderator_category(data) => (
            category_text(data).to_string(),
            category_back_keyboard("back_nonmoderator"),
        ),
        _ => (category_text(data).to_string(), help_keyboard()),
    }
}

pub async fn handle_start(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let mention = msg
        .from()
        .map(|u| {
            u.username
                .as_ref()
                .map(|un| format!("@{}", un))
                .unwrap_or_else(|| u.first_name.clone())
        })
        .unwrap_or_else(|| "there".to_string());
    let mention = crate::utils::escape_html(&mention);

    let caption = start_text(&mention);
    let keyboard = start_keyboard();

    let msg_id =
        if let Ok(Some((data, _mime))) = crate::db::assets::get_asset(client, "welcome").await {
            bot.send_photo_file(
                msg.chat.id,
                "welcome.jpg",
                data,
                Some(caption),
                Some(crate::telegram::ParseMode::Html),
                Some(keyboard),
            )
            .await?
        } else {
            let photo_url = std::env::var("START_PHOTO_URL")
                .unwrap_or_else(|_| "https://i.imgur.com/example-robin-welcome.jpg".to_string());

            bot.send_photo(msg.chat.id, photo_url)
                .caption(Some(caption))
                .parse_mode(crate::telegram::ParseMode::Html)
                .reply_markup(keyboard)
                .await?
        };

    bot.track_menu(msg.chat.id, msg_id.id() as i64, true);
    Ok(())
}

pub async fn handle_help(bot: Bot, msg: Message) -> Result<(), String> {
    let _ = bot
        .edit_menu_or_send(
            msg.chat.id,
            help_text(),
            Some(ParseMode::Html),
            Some(help_keyboard()),
        )
        .await;
    Ok(())
}

pub async fn handle_help_or_about(bot: Bot, msg: Message, _client: &Client, is_about: bool) -> Result<(), String> {
    let mention = msg
        .from()
        .map(|u| {
            u.username
                .as_ref()
                .map(|un| format!("@{}", un))
                .unwrap_or_else(|| u.first_name.clone())
        })
        .unwrap_or_else(|| "there".to_string());
    let mention = crate::utils::escape_html(&mention);
    
    let (text, keyboard) = if is_about {
        (about_text(), category_back_keyboard("back_start"))
    } else {
        (help_text().to_string(), help_keyboard())
    };
    
    let _ = bot
        .edit_menu_or_send(
            msg.chat.id,
            &text,
            Some(ParseMode::Html),
            Some(keyboard),
        )
        .await;
    Ok(())
}

fn category_text(category: &str) -> &'static str {
    match category {
        "cat_profile" => concat!(
            "🌸 <b>Profile Commands</b> 🌸\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "👤 /profile [@user | ID]  —  <b>[Card]</b>\n",
            "   · Action: Renders complete user profile card (photo, username, role, ID, bio, join date).\n",
            "   · How to use: Send /profile for yourself, reply to a user with /profile, or send /profile @username.\n\n",
            "📝 /setbio &lt;text&gt;  —  <b>[Biography]</b>\n",
            "   · Action: Stores a custom biography message displayed on your profile card.\n",
            "   · How to use: Send /setbio Hello! I am a group co-host.\n\n",
            "📦 /exportmydata  —  <b>[Export]</b>\n",
            "   · Action: Generates a complete JSON export of all your stored database records.\n",
            "   · How to use: Send /exportmydata in private DM with the bot to download your data file.\n\n",
            "🗑 /deletemydata  —  <b>[Erasure]</b>\n",
            "   · Action: Permanently deletes all your saved database records.\n",
            "   · How to use: Send /deletemydata in private DM with the bot to wipe your data.\n\n",
            "👥 /staff  —  <b>[Roster]</b>\n",
            "   · Action: Scans the chat hierarchy and lists all group owners and active administrators.\n",
            "   · How to use: Send /staff in a group chat to display the staff roster.",
        ),
        "cat_notes" => concat!(
            "📝 <b>Notes Commands</b> 📝\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "💾 /save &lt;keyword&gt; &lt;content&gt;  —  <b>[Store]</b>\n",
            "   · Action: Stores text, links, or media under a keyword trigger scoped to this group.\n",
            "   · How to use: Send /save rules Read guidelines OR reply to a message with /save faq.\n\n",
            "🔍 /get &lt;keyword&gt;  —  <b>[Retrieve]</b>\n",
            "   · Action: Looks up and posts the saved content associated with a note keyword.\n",
            "   · How to use: Send /get rules OR type #rules anywhere in the group chat.\n\n",
            "📋 /notes  —  <b>[Catalog]</b>\n",
            "   · Action: Lists all saved note keywords stored in this group database.\n",
            "   · How to use: Send /notes in the group to view all available note triggers.\n\n",
            "🗑 /clear &lt;keyword&gt;  —  <b>[Remove]</b>\n",
            "   · Action: Permanently deletes a saved note from the group database by its keyword.\n",
            "   · How to use: Send /clear rules to delete the note saved under rules.",
        ),
        "cat_moderation" => concat!(
            "⚔️ <b>Moderation Commands</b> ⚔️\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "🚫 /ban [@user] [reason]  —  <b>[Ban]</b>\n",
            "   · Action: Permanently bans a user from the chat and deletes recent activity.\n",
            "   · How to use: Reply to a message with /ban Spamming OR send /ban @username Excessive ads.\n\n",
            "✅ /unban [@user]  —  <b>[Unban]</b>\n",
            "   · Action: Removes a user from the group ban list so they can rejoin via invite link.\n",
            "   · How to use: Reply to a user with /unban OR send /unban @username.\n\n",
            "👢 /kick [@user] [reason]  —  <b>[Remove]</b>\n",
            "   · Action: Kicks a user from the group without a permanent ban (they can rejoin via link).\n",
            "   · How to use: Reply to a message with /kick Please follow guidelines.\n\n",
            "🔇 /mute [@user] [reason]  —  <b>[Mute]</b>\n",
            "   · Action: Restricts a user's permission to send text, media, or links in the group.\n",
            "   · How to use: Reply to a message with /mute Disruption in chat.\n\n",
            "🔊 /unmute [@user]  —  <b>[Unmute]</b>\n",
            "   · Action: Restores full chat messaging permissions to a muted user.\n",
            "   · How to use: Reply to a user with /unmute OR send /unmute @username.\n\n",
            "⚠️ /warn [@user] [reason]  —  <b>[Warning]</b>\n",
            "   · Action: Issues an official warning to a user (auto-bans upon reaching 3 warnings).\n",
            "   · How to use: Reply to a message with /warn Inappropriate language.\n\n",
            "📋 /warns [@user]  —  <b>[Inspection]</b>\n",
            "   · Action: Displays a user's total warning count and detailed reasons for each warning.\n",
            "   · How to use: Reply to a user's message with /warns OR send /warns @username.\n\n",
            "🔄 /resetwarn [@user]  —  <b>[Clear]</b>\n",
            "   · Action: Clears all warning records for a user, resetting count back to 0.\n",
            "   · How to use: Reply to a user's message with /resetwarn OR send /resetwarn @username.\n\n",
            "🐢 /slowmode &lt;seconds&gt;  —  <b>[Delay]</b>\n",
            "   · Action: Enforces required wait time (seconds) between non-admin messages (0 disables).\n",
            "   · How to use: Send /slowmode 15 to require a 15-second wait between messages.\n\n",
            "❌ /del  —  <b>[Delete]</b>\n",
            "   · Action: Immediately deletes the replied-to message and the /del command call.\n",
            "   · How to use: Reply to any unwanted message with /del.\n\n",
            "📌 /pin  —  <b>[Highlight]</b>\n",
            "   · Action: Pins the replied-to message to the group chat header banner.\n",
            "   · How to use: Reply to an announcement message with /pin.\n\n",
            "📌 /unpin [all]  —  <b>[Unhighlight]</b>\n",
            "   · Action: Unpins a specific pinned message or clears all pinned messages.\n",
            "   · How to use: Reply to a pinned message with /unpin OR send /unpin all.\n\n",
            "⚡ /autowarnon  —  <b>[Enable]</b>\n",
            "   · Action: Turns on automatic warning issuance for repeat spam/security offenders.\n",
            "   · How to use: Send /autowarnon in the group chat.\n\n",
            "⚡ /autowarnoff  —  <b>[Disable]</b>\n",
            "   · Action: Turns off automatic warning issuance.\n",
            "   · How to use: Send /autowarnoff in the group chat.\n\n",
            "🧹 /purge [count]  —  <b>[Clean]</b>\n",
            "   · Action: Bulk deletes messages (replying deletes target and all after; number deletes last N).\n",
            "   · How to use: Reply to start message with /purge OR send /purge 20.\n\n",
            "⏱ /tmute [@user] &lt;duration&gt;  —  <b>[Temporary-mute]</b>\n",
            "   · Action: Mutes a user temporarily for a duration (e.g. 30m = 30 min, 2h = 2 hrs, 1d = 1 day).\n",
            "   · How to use: Reply to a message with /tmute 2h to silence for 2 hours.\n\n",
            "⏱ /tban [@user] &lt;duration&gt;  —  <b>[Temporary-ban]</b>\n",
            "   · Action: Bans a user temporarily for a duration (e.g. 1h, 1d, 1w). Unbans automatically.\n",
            "   · How to use: Send /tban @username 1d to ban for 1 day.\n\n",
            "👋 /kickme  —  <b>[Self-remove]</b>\n",
            "   · Action: Removes yourself from the current group chat.\n",
            "   · How to use: Send /kickme in the group chat.",
        ),
        "cat_filters" => concat!(
            "🔍 <b>Filters Commands</b> 🔍\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "➕ /filter &lt;trigger&gt; &lt;response&gt;  —  <b>[Auto-reply]</b>\n",
            "   · Action: Configures auto-reply rule: whenever trigger appears, bot posts response.\n",
            "   · How to use: Send /filter website https://example.com to auto-reply on website.\n\n",
            "⛔ /stop &lt;trigger&gt;  —  <b>[Delete]</b>\n",
            "   · Action: Removes an active auto-reply filter trigger from the group.\n",
            "   · How to use: Send /stop website to stop auto-replying on website.\n\n",
            "📋 /filters  —  <b>[Overview]</b>\n",
            "   · Action: Lists all active trigger-and-response rules configured in the group.\n",
            "   · How to use: Send /filters in the group chat to view active rules.",
        ),
        "cat_welcome" => concat!(
            "👋 <b>Welcome Commands</b> 👋\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "✏️ /setwelcome &lt;msg&gt;  —  <b>[Welcome]</b>\n",
            "   · Action: Sets custom joining message ({user} = name, {group} = title, {count} = total).\n",
            "   · How to use: Send /setwelcome Welcome {user} to {group}! Member #{count}.\n\n",
            "🗑 /resetwelcome  —  <b>[Reset]</b>\n",
            "   · Action: Clears custom welcome message and restores default bot greeting.\n",
            "   · How to use: Send /resetwelcome in the group chat.\n\n",
            "👁 /welcome  —  <b>[Preview]</b>\n",
            "   · Action: Renders a live preview of the active welcome greeting message.\n",
            "   · How to use: Send /welcome in the group chat.\n\n",
            "💌 /setwelcomedm &lt;msg&gt;  —  <b>[Direct-message]</b>\n",
            "   · Action: Configures a private welcome message sent directly to new members in DM.\n",
            "   · How to use: Send /setwelcomedm Thanks for joining {group}! Please read our rules.\n\n",
            "👋 /setfarewell &lt;msg&gt;  —  <b>[Farewell]</b>\n",
            "   · Action: Sets the goodbye message posted when a member leaves ({user}, {group}).\n",
            "   · How to use: Send /setfarewell Goodbye {user}, hope to see you again in {group}!\n\n",
            "👁 /farewell  —  <b>[Preview]</b>\n",
            "   · Action: Displays a live preview of the configured farewell message.\n",
            "   · How to use: Send /farewell in the group chat.\n\n",
            "🧹 /cleanwelcome  —  <b>[Auto-delete]</b>\n",
            "   · Action: Toggles automatic deletion of welcome messages after 60 seconds.\n",
            "   · How to use: Send /cleanwelcome to turn auto-cleaning ON or OFF.\n\n",
            "🧪 /welcometest  —  <b>[Test]</b>\n",
            "   · Action: Simulates a join event using your username and member count to test formatting.\n",
            "   · How to use: Send /welcometest in the group chat.",
        ),
        "cat_security" => concat!(
            "🔒 <b>Security Commands</b> 🔒\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "🌊 /setflood &lt;count&gt;  —  <b>[Limit]</b>\n",
            "   · Action: Sets maximum allowed messages per user in 10 seconds (0 disables).\n",
            "   · How to use: Send /setflood 5 to limit to 5 messages per 10 seconds.\n\n",
            "📊 /flood  —  <b>[Status]</b>\n",
            "   · Action: Displays current anti-flood security settings including limit and mode.\n",
            "   · How to use: Send /flood in the group chat.\n\n",
            "🤬 /addswear &lt;word&gt;  —  <b>[Block]</b>\n",
            "   · Action: Adds a word to the bad word blacklist. Matching messages are deleted & warned.\n",
            "   · How to use: Send /addswear badword to block badword.\n\n",
            "🗑 /delswear &lt;word&gt;  —  <b>[Unblock]</b>\n",
            "   · Action: Removes a word from the group bad word blacklist.\n",
            "   · How to use: Send /delswear badword to unblock badword.\n\n",
            "🚨 /report  —  <b>[Flag]</b>\n",
            "   · Action: Flags an inappropriate message directly to all group admins and log channel.\n",
            "   · How to use: Reply to any spam or offensive message with /report.",
        ),
        "cat_rules" => concat!(
            "📜 <b>Rules Commands</b> 📜\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "✏️ /setrules &lt;text&gt;  —  <b>[Rules]</b>\n",
            "   · Action: Saves the official group rules document in the database.\n",
            "   · How to use: Send /setrules 1. Be respectful\\n2. No spam\\n3. No promo.\n\n",
            "📖 /rules  —  <b>[Display]</b>\n",
            "   · Action: Displays the official group rules document.\n",
            "   · How to use: Send /rules in any group chat.\n\n",
            "🗑 /clearrules  —  <b>[Erase]</b>\n",
            "   · Action: Permanently deletes the saved group rules document.\n",
            "   · How to use: Send /clearrules in the group chat.",
        ),
        "cat_locks" => concat!(
            "🔐 <b>Locks Commands</b> 🔐\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "🔒 /lock &lt;type&gt;  —  <b>[Lock]</b>\n",
            "   · Action: Blocks media types (photos, videos, stickers, gifs, links, bots, polls, etc.).\n",
            "   · How to use: Send /lock links to block links, or /lock stickers to block stickers.\n\n",
            "🔓 /unlock &lt;type&gt;  —  <b>[Unlock]</b>\n",
            "   · Action: Unlocks a previously restricted media or content type.\n",
            "   · How to use: Send /unlock links to permit links again.\n\n",
            "📋 /locks  —  <b>[Audit]</b>\n",
            "   · Action: Displays all currently enforced content locks in the group.\n",
            "   · How to use: Send /locks in the group chat.",
        ),
        "cat_features" => concat!(
            "⭐ <b>Features Commands</b> ⭐\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "📋 /features  —  <b>[List]</b>\n",
            "   · Action: Displays ON/OFF feature override status for the chat.\n",
            "   · How to use: Send /features in the group chat.\n\n",
            "✅ /enable &lt;feature&gt;  —  <b>[Enable]</b>\n",
            "   · Action: Activates a specific feature module (filters, notes, locks, security, etc.).\n",
            "   · How to use: Send /enable filters to turn on auto-replies.\n\n",
            "❌ /disable &lt;feature&gt;  —  <b>[Disable]</b>\n",
            "   · Action: Deactivates a specific feature module for the group.\n",
            "   · How to use: Send /disable locks to turn off content locking.\n\n",
            "🔄 /toggle &lt;feature&gt;  —  <b>[Switch]</b>\n",
            "   · Action: Flips a feature state between enabled and disabled.\n",
            "   · How to use: Send /toggle welcome.\n\n",
            "📁 /enablecategory &lt;cat&gt;  —  <b>[Enable-category]</b>\n",
            "   · Action: Enables every feature inside a category at once.\n",
            "   · How to use: Send /enablecategory moderation.\n\n",
            "📁 /disablecategory &lt;cat&gt;  —  <b>[Disable-category]</b>\n",
            "   · Action: Disables every feature inside a category at once.\n",
            "   · How to use: Send /disablecategory fun.\n\n",
            "ℹ️ /featureinfo  —  <b>[Guide]</b>\n",
            "   · Action: Displays category-to-feature mapping details.\n",
            "   · How to use: Send /featureinfo in the group chat.\n\n",
            "👤 /myfeatures  —  <b>[Summary]</b>\n",
            "   · Action: Displays summary counts of enabled vs disabled features.\n",
            "   · How to use: Send /myfeatures in the group chat.\n\n",
            "🔄 /resetfeatures  —  <b>[Restore]</b>\n",
            "   · Action: Resets all feature overrides to default (all enabled).\n",
            "   · How to use: Send /resetfeatures in the group chat.",
        ),
        "cat_federation" => concat!(
            "🌐 <b>Federation Commands</b> 🌐\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "➕ /newfed &lt;name&gt;  —  <b>[Create]</b>\n",
            "   · Action: Initializes a new multi-group federation under name and generates an ID.\n",
            "   · How to use: Send /newfed Anime Alliance to create a federation.\n\n",
            "🔗 /joinfed &lt;fed_id&gt;  —  <b>[Connect]</b>\n",
            "   · Action: Connects the current group to an existing federation by its 8-character ID.\n",
            "   · How to use: Send /joinfed a1b2c3d4 to link your group.\n\n",
            "🌍 /gban @user &lt;reason&gt;  —  <b>[Global-ban]</b>\n",
            "   · Action: Bans a user globally across all groups managed by the bot.\n",
            "   · How to use: Send /gban @username Malicious raid bot.\n\n",
            "🌍 /ungban @user  —  <b>[Global-unban]</b>\n",
            "   · Action: Removes a user from the global ban list.\n",
            "   · How to use: Send /ungban @username.\n\n",
            "📋 /gbans  —  <b>[Global-list]</b>\n",
            "   · Action: Displays all users currently on the global ban list.\n",
            "   · How to use: Send /gbans in the chat.",
        ),
        "cat_fun" => concat!(
            "🎨 <b>Fun Commands</b> 🎨\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "💬 /q [n]  —  <b>[Quote]</b>\n",
            "   · Action: Renders a replied-to message (or last N messages) into a styled image quote card.\n",
            "   · How to use: Reply to a message with /q OR reply with /q 2 / /q 3.",
        ),
        "cat_game" => concat!(
            "📜 <b>Poneglyph Games — The Grand Line</b> 📜\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "History is not erased by silence, dear pirate. Let us inscribe your tale in the ",
            "<b>Wanted Ledger</b> — every bounty you earn draws you closer to the truth of the ",
            "Void Century.\n\n",
            "💰 <b>1 · The Wanted Ledger</b> — your bounty in Berries. It never falls below 0.\n",
            "   📅 /daily — The <b>Log Pose</b> realigns: claim <b>+5</b> Berries once per day.\n",
            "   🧠 /quiz — <b>Poneglyph Quiz</b>: decipher a riddle left by the scholars of Ohara. ",
            "Correct: <b>+10</b>. Wrong: <b>-5</b>.\n",
             "   🌊 /voyage — <b>Grand Line Voyage</b>: sail for fortune or ruin (1h per-user cooldown). ",
             "+8 to +20 if the sea smiles... -5 to -10 if it remembers you.\n\n",
             "⚓ <b>2 · Pirate Crews</b> — bonds forged on the sea\n",
             "   A crew's bounty is the <b>sum of all members' bounties</b>.\n",
             "   /crew create &lt;name&gt; — Found your crew and become Captain\n",
             "   /crew invite — Reply to a pirate to extend an invitation\n",
             "   /crew invites — Read your pending invitations\n",
             "   /crew join &lt;id&gt; — Accept an invitation\n",
             "   /crew reject &lt;id&gt; — Decline an invitation\n",
             "   /crew info — Gaze upon your crew's ledger\n",
             "   /crew leave — Part ways with your crew\n",
             "   /crew disband — Scatter the crew to the winds (Captain only)\n\n",
             "🏆 <b>3 · Wanted Posters &amp; Stats</b>\n",
             "   /leaderboard — The world's most notorious pirates\n",
             "   /toppirates — Top 10 pirates with crew affiliation\n",
             "   /crewlb — The most infamous crews of the Grand Line\n",
             "   /crewboard — Crew rankings with averages &amp; voyages\n",
             "   /mystats — Your bounty, voyages, wins and crew\n",
             "   /crewstats — Your crew's aggregate statistics\n",
             "   /cooldown [game] — Check your remaining cooldowns\n\n",
             "⚠️ <b>Rules of the Sea</b>\n",
             "   • Bounty never drops below 0\n",
             "   • Quiz: one attempt per pirate, a strict timer, and only the first correct answer is rewarded\n",
             "   • Voyage: 1 hour per-user cooldown — the sea is merciless\n",
             "   • No inflation: storms and wrong answers keep the ledger honest",
        ),
        _ => "Unknown category.",
    }
}

pub async fn handle_category_callback(
    bot: Bot,
    cq: CallbackQuery,
    _client: &Client,
) -> Result<(), String> {
    let _ = bot.answer_callback_query(&cq.id).await;

    if let Some(data) = cq.data {
        let (chat_id, message_id, is_photo) = match cq.message.as_ref() {
            Some(m) => (m.chat.id, m.id() as i64, m.photo.is_some()),
            None => return Ok(()),
        };

        let mention = cq
            .from
            .username
            .as_ref()
            .map(|un| format!("@{}", un))
            .unwrap_or_else(|| cq.from.first_name.clone());
        let mention = crate::utils::escape_html(&mention);

        let (text, markup) = page_for(&data, &mention);
        let _ = bot
            .edit_menu_message(
                chat_id,
                message_id,
                is_photo,
                &text,
                Some(ParseMode::Html),
                Some(markup),
            )
            .await;
    }

    Ok(())
}
