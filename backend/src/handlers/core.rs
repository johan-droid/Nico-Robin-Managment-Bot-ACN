use crate::telegram::api::Bot;
use crate::telegram::ParseMode;
use crate::telegram::update::{
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message,
};
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

fn start_keyboard() -> InlineKeyboardMarkup {
    let bot_username = std::env::var("BOT_USERNAME")
        .unwrap_or_else(|_| std::env::var("BOT_NAME").unwrap_or_else(|_| "nico_robin_bot".to_string()))
        .replace(' ', "_")
        .to_lowercase();
    let bot_name = std::env::var("BOT_NAME").unwrap_or_else(|_| "Nico Robin".to_string());
    InlineKeyboardMarkup {
        inline_keyboard: vec![
            vec![_url_btn(
                &format!("➕ Add {} to your group", bot_name),
                &format!("https://t.me/{}?startgroup=true", bot_username),
            )],
            vec![
                _btn("❓ Help", "help"),
                _btn("ℹ️ About", "about"),
            ],
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

fn help_keyboard() -> InlineKeyboardMarkup {
    InlineKeyboardMarkup {
        inline_keyboard: vec![
            vec![_btn("🛡️ Moderator Commands", "moderator")],
            vec![_btn("👤 Non-Moderator Commands", "nonmoderator")],
        ],
    }
}

fn category_keyboard(categories: &[(&str, &str)]) -> InlineKeyboardMarkup {
    let mut rows: Vec<Vec<InlineKeyboardButton>> = categories
        .chunks(2)
        .map(|chunk| chunk.iter().map(|(label, cb)| _btn(label, cb)).collect())
        .collect();
    rows.push(vec![_btn("🔙 Back", "back")]);
    InlineKeyboardMarkup { inline_keyboard: rows }
}

fn moderator_keyboard() -> InlineKeyboardMarkup {
    category_keyboard(MODERATOR_CATEGORIES)
}

fn non_moderator_keyboard() -> InlineKeyboardMarkup {
    category_keyboard(NON_MODERATOR_CATEGORIES)
}

fn category_back_keyboard() -> InlineKeyboardMarkup {
    InlineKeyboardMarkup {
        inline_keyboard: vec![
            vec![_btn("🔙 Back", "back")],
        ],
    }
}

fn is_moderator_category(cb: &str) -> bool {
    MODERATOR_CATEGORIES.iter().any(|(_, c)| *c == cb)
}

fn is_non_moderator_category(cb: &str) -> bool {
    NON_MODERATOR_CATEGORIES.iter().any(|(_, c)| *c == cb)
}

fn back_keyboard_for(cb: &str) -> InlineKeyboardMarkup {
    if is_moderator_category(cb) {
        moderator_keyboard()
    } else if is_non_moderator_category(cb) {
        non_moderator_keyboard()
    } else {
        help_keyboard()
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

    let caption = format!(
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
    );
    let keyboard = start_keyboard();

    if let Ok(Some((data, _mime))) = crate::db::assets::get_asset(client, "welcome").await {
        bot.send_photo_file(
            msg.chat.id,
            "welcome.jpg",
            data,
            Some(caption),
            Some(crate::telegram::ParseMode::Html),
            Some(keyboard),
        )
            .await?;
        return Ok(());
    }

    let photo_url = std::env::var("START_PHOTO_URL")
        .unwrap_or_else(|_| "https://i.imgur.com/example-robin-welcome.jpg".to_string());

    bot.send_photo(msg.chat.id, photo_url)
        .caption(Some(caption))
        .parse_mode(crate::telegram::ParseMode::Html)
        .reply_markup(keyboard)
        .await?;

    Ok(())
}

pub async fn handle_help(bot: Bot, msg: Message) -> Result<(), String> {
    let text = concat!(
        "📖 <b>Nico Robin Bot — Commands</b>\n\n",
        "🛡️ <b>Moderator Commands</b> — admin &amp; management tools\n",
        "👤 <b>Non-Moderator Commands</b> — commands for everyone\n\n",
        "Tap a category to see its commands:",
    );
    let _ = bot
        .send_or_edit(msg.chat.id, text, Some(ParseMode::Html), Some(help_keyboard()))
        .await;
    Ok(())
}

fn category_text(category: &str) -> &'static str {
    match category {
        "cat_profile" => concat!(
            "🌸 <b>Profile</b> 🌸\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "👤 /profile  —  View your profile card\n",
            "   · Use it to see your bio, join date and saved info.\n",
            "📝 /setbio &lt;text&gt;  —  Set your bio\n",
            "   · Use it to introduce yourself to the group.\n",
            "📦 /exportmydata  —  Export your data\n",
            "   · Use it to download a copy of everything the bot saved about you.\n",
            "🗑 /deletemydata  —  Delete your data\n",
            "   · Use it to erase all your data (captain/dev only).\n",
            "👥 /staff  —  View the staff list\n",
            "   · Use it to see the owners and admins of this group.",
        ),
        "cat_notes" => concat!(
            "📝 <b>Notes</b> 📝\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "💾 /save &lt;name&gt; &lt;content&gt;  —  Save a note\n",
            "   · Use it to store FAQs, links or rules under a name.\n",
            "🔍 /get &lt;name&gt;  —  Get a note\n",
            "   · Use it to quickly pull up a saved note.\n",
            "📋 /notes  —  List all notes\n",
            "   · Use it to see every note saved in this group.\n",
            "🗑 /clear &lt;name&gt;  —  Delete a note\n",
            "   · Use it to remove a note you no longer need.",
        ),
        "cat_moderation" => concat!(
            "⚔️ <b>Moderation</b> ⚔️\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "🚫 /ban @user  —  Ban a user\n",
            "   · Use it to permanently block spammers or troublemakers.\n",
            "✅ /unban @user  —  Unban a user\n",
            "   · Use it to let a banned user back in.\n",
            "👢 /kick @user  —  Kick a user\n",
            "   · Use it to remove someone temporarily (they can rejoin).\n",
            "🔇 /mute @user  —  Mute a user\n",
            "   · Use it to silence a noisy user without removing them.\n",
            "🔊 /unmute @user  —  Unmute a user\n",
            "   · Use it to restore a muted user's ability to chat.\n",
            "⚠️ /warn @user  —  Warn a user\n",
            "   · Use it to flag rule-breakers before taking harsher action.\n",
            "📋 /warns @user  —  Show warnings\n",
            "   · Use it to check how many warnings a user has.\n",
            "🔄 /resetwarn @user  —  Reset warnings\n",
            "   · Use it to clear a user's warning history.\n",
            "🐢 /slowmode &lt;s&gt;  —  Set slowmode\n",
            "   · Use it to require a wait (seconds) between messages.\n",
            "❌ /del  —  Delete replied message\n",
            "   · Use it to remove a specific unwanted message.\n",
            "📌 /pin  —  Pin replied message\n",
            "   · Use it to highlight an important message.\n",
            "⚡ /autowarnon  —  Enable auto-warn\n",
            "   · Use it to warn repeat offenders automatically.\n",
            "⚡ /autowarnoff  —  Disable auto-warn\n",
            "   · Use it to turn automatic warnings off.\n",
            "🧹 /purge  —  Purge messages\n",
            "   · Reply to a message to delete it and everything after, or use /purge &lt;count&gt; to delete the last n messages.\n",
            "⏱ /tmute @user &lt;duration&gt;  —  Temporary mute\n",
            "   · Use it to mute someone for a set time (e.g. 30m, 2h, 1d).\n",
            "⏱ /tban @user &lt;duration&gt;  —  Temporary ban\n",
            "   · Use it to ban someone for a set time (e.g. 1h, 1d, 1w).\n",
            "👋 /kickme  —  Leave the group\n",
            "   · Use it to remove yourself from the group.\n",
            "📌 /pin  —  Pin a message\n",
            "   · Reply to a message to pin it in the group.\n",
            "📌 /unpin  —  Unpin a message\n",
            "   · Reply to a message to unpin it, or use /unpin all to clear every pin.",
        ),
        "cat_filters" => concat!(
            "🔍 <b>Filters</b> 🔍\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "➕ /filter &lt;trigger&gt; &lt;response&gt;  —  Add auto-reply\n",
            "   · Use it to auto-answer common questions when someone says a keyword.\n",
            "⛔ /stop &lt;trigger&gt;  —  Remove a filter\n",
            "   · Use it to delete an auto-reply you no longer want.\n",
            "📋 /filters  —  List all filters\n",
            "   · Use it to review every active auto-reply in the group.",
        ),
        "cat_welcome" => concat!(
            "👋 <b>Welcome</b> 👋\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "✏️ /setwelcome &lt;msg&gt;  —  Set welcome message\n",
            "   · Use it to greet new members when they join.\n",
            "🗑 /resetwelcome  —  Remove welcome message\n",
            "   · Use it to go back to the default greeting.\n",
            "👁 /welcome  —  Preview welcome message\n",
            "   · Use it to see how the greeting looks before it's sent.\n",
            "💌 /setwelcomedm &lt;msg&gt;  —  Set DM to new members\n",
            "   · Use it to send new members a private message (e.g. rules).\n",
            "👋 /setfarewell &lt;msg&gt;  —  Set farewell message\n",
            "   · Use it to say goodbye when someone leaves.\n",
            "👁 /farewell  —  Preview farewell\n",
            "   · Use it to check the farewell before it's sent.\n",
            "🧹 /cleanwelcome  —  Toggle auto-delete welcome\n",
            "   · Use it to automatically remove welcome messages after a while.\n",
            "🧪 /welcometest  —  Test welcome with your name\n",
            "   · Use it to preview the welcome as a regular member.",
        ),
        "cat_security" => concat!(
            "🔒 <b>Security</b> 🔒\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "🌊 /setflood &lt;count&gt;  —  Set flood limit\n",
            "   · Use it to set how many messages trigger anti-spam.\n",
            "📊 /flood  —  Show flood settings\n",
            "   · Use it to check the current flood limit.\n",
            "🤬 /addswear &lt;word&gt;  —  Add swear word\n",
            "   · Use it to add a word the bot should watch for.\n",
            "🗑 /delswear &lt;word&gt;  —  Remove swear word\n",
            "   · Use it to stop watching a previously added word.\n",
            "🚨 /report  —  Report a message\n",
            "   · Reply to a message to flag it to the group admins.",
        ),
        "cat_rules" => concat!(
            "📜 <b>Rules</b> 📜\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "✏️ /setrules &lt;text&gt;  —  Set group rules\n",
            "   · Use it to store the rules members must follow.\n",
            "📖 /rules  —  View group rules\n",
            "   · Use it to read the rules at any time.\n",
            "🗑 /clearrules  —  Clear group rules\n",
            "   · Use it to remove the rules entirely.",
        ),
        "cat_locks" => concat!(
            "🔐 <b>Locks</b> 🔐\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "🔒 /lock &lt;type&gt;  —  Lock content type\n",
            "   · Block photos, videos, stickers, gifs, links, forwards, bots and more.\n",
            "🔓 /unlock &lt;type&gt;  —  Unlock content type\n",
            "   · Use it to allow a previously locked content type again.\n",
            "📋 /locks  —  List active locks\n",
            "   · Use it to see which content types are locked in this group.",
        ),
        "cat_features" => concat!(
            "⭐ <b>Features</b> ⭐\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "📋 /features  —  List all features\n",
            "   · Use it to see which features are ON or OFF for this group.\n",
            "✅ /enable &lt;name&gt;  —  Enable a feature\n",
            "   · Use it to turn a disabled feature back on.\n",
            "❌ /disable &lt;name&gt;  —  Disable a feature\n",
            "   · Use it to turn off a feature you don't want in the group.\n",
            "🔄 /toggle &lt;name&gt;  —  Toggle a feature\n",
            "   · Use it as a quick on/off switch for a feature.\n",
            "ℹ️ /featureinfo  —  Feature details\n",
            "   · Use it to see what each feature and category controls.\n",
            "👤 /myfeatures  —  Your enabled features\n",
            "   · Use it to see how many features this group has on/off.\n",
            "🔄 /resetfeatures  —  Reset all features\n",
            "   · Use it to put every feature back to default (on).\n",
            "📁 /enablecategory &lt;cat&gt;  —  Enable category\n",
            "   · Use it to turn on an entire group of features at once.\n",
            "📁 /disablecategory &lt;cat&gt;  —  Disable category\n",
            "   · Use it to turn off an entire group of features at once.",
        ),
        "cat_federation" => concat!(
            "🌐 <b>Federation</b> 🌐\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "➕ /newfed &lt;name&gt;  —  Create a federation\n",
            "   · Use it to create a shared group of connected groups.\n",
            "🔗 /joinfed &lt;fed_id&gt;  —  Join group to federation\n",
            "   · Use it to link this group to an existing federation.\n",
            "🌍 /gban @user &lt;reason&gt;  —  Global ban\n",
            "   · Ban a user from every group the bot manages at once.\n",
            "🌍 /ungban @user  —  Remove global ban\n",
            "   · Use it to clear a user from the global ban list.\n",
            "📋 /gbans  —  List global bans\n",
            "   · Use it to see everyone on the global ban list.",
        ),
        "cat_fun" => concat!(
            "🎨 <b>Fun</b> 🎨\n",
            "✿ ∘ ━━━━━━━━━┉┅╍\n\n",
            "💬 /q  —  Quote a message as an image\n",
            "   · Reply to a message and use it to turn it into a shareable quote.\n",
            "💬 /q &lt;n&gt;  —  Quote the last n messages\n",
            "   · Use it like /q2 or /q3 to quote the last 2, 3… messages.",
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
        let (chat_id, message_id) = match cq.message.as_ref() {
            Some(m) => (m.chat.id, m.id()),
            None => return Ok(()),
        };

        if data == "help" {
            let text = concat!(
                "📖 <b>Nico Robin Bot — Commands</b>\n\n",
                "🛡️ <b>Moderator Commands</b> — admin &amp; management tools\n",
                "👤 <b>Non-Moderator Commands</b> — commands for everyone\n\n",
                "Tap a category to see its commands:",
            );
            let _ = bot
                .send_or_edit(chat_id, text, Some(ParseMode::Html), Some(help_keyboard()))
                .await;
            return Ok(());
        }

        if data == "moderator" {
            let text = concat!(
                "🛡️ <b>Moderator Commands</b> 🛡️\n\n",
                "Admin &amp; management tools. Tap a category to see its commands:",
            );
            let _ = bot
                .send_or_edit(chat_id, text, Some(ParseMode::Html), Some(moderator_keyboard()))
                .await;
            return Ok(());
        }

        if data == "nonmoderator" {
            let text = concat!(
                "👤 <b>Non-Moderator Commands</b> 👤\n\n",
                "Commands available to everyone. Tap a category to see its commands:",
            );
            let _ = bot
                .send_or_edit(chat_id, text, Some(ParseMode::Html), Some(non_moderator_keyboard()))
                .await;
            return Ok(());
        }

        if data == "about" {
            let bot_name = std::env::var("BOT_NAME").unwrap_or_else(|_| "Nico Robin".to_string());
            let text = format!(
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
            );
            let _ = bot
                .send_or_edit(chat_id, &text, Some(ParseMode::Html), Some(category_back_keyboard()))
                .await;
            return Ok(());
        }

        let is_back = data == "back";

        let text = if is_back {
            concat!(
                "📖 <b>Nico Robin Bot — Commands</b>\n\n",
                "🛡️ <b>Moderator Commands</b> — admin &amp; management tools\n",
                "👤 <b>Non-Moderator Commands</b> — commands for everyone\n\n",
                "Tap a category to see its commands:",
            )
        } else {
            category_text(&data)
        };
        let markup = if is_back {
            help_keyboard()
        } else {
            back_keyboard_for(&data)
        };

        let payload = serde_json::json!({
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": serde_json::to_value(markup).unwrap_or_default(),
        });
        let _ = bot.api_post("editMessageText", payload).await;
    }

    Ok(())
}
