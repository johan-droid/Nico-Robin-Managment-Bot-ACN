use teloxide::prelude::*;
use crate::utils::escape_md_v2;

pub async fn handle_start(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    let name = msg
        .from()
        .map(|u| u.first_name.as_str())
        .unwrap_or("there");
    bot.send_message(
        msg.chat.id,
        format!(
            "🌿 Welcome {}! I'm Nico Robin Bot.\n\nI help manage your group with moderation, notes, filters, welcome messages, and more.\n\nUse /help to see all available commands.",
            name
        ),
    )
    .await?;
    Ok(())
}

pub async fn handle_help(bot: Bot, msg: Message) -> Result<(), teloxide::RequestError> {
    use teloxide::types::ParseMode::MarkdownV2;

    let sections: Vec<(&str, &str, &[(&str, &str)])> = vec![
        ("Core", "everyone", &[
            ("/start", "Welcome message"),
            ("/help", "Show this help"),
        ]),
        ("Profile", "everyone", &[
            ("/profile", "View your profile"),
            ("/setbio <text>", "Set your bio"),
            ("/exportmydata", "Export your data"),
            ("/deletemydata", "Delete your data"),
        ]),
        ("Notes", "everyone", &[
            ("/save <name> <content>", "Save a note"),
            ("/get <name>", "Get a note"),
            ("/notes", "List all notes"),
            ("/clear <name>", "Delete a note"),
        ]),
        ("Moderation", "Admins", &[
            ("/ban @user", "Ban a user"),
            ("/unban @user", "Unban a user"),
            ("/kick @user", "Kick a user"),
            ("/mute @user", "Mute a user"),
            ("/unmute @user", "Unmute a user"),
            ("/warn @user", "Warn a user"),
            ("/warns @user", "Show warnings"),
            ("/resetwarn @user", "Reset warnings"),
            ("/slowmode <s>", "Set slowmode (0 = off)"),
            ("/del", "Delete replied message"),
            ("/pin", "Pin replied message"),
        ]),
        ("Filters", "Admins", &[
            ("/filter <trigger> <response>", "Add auto-reply filter"),
            ("/stop <trigger>", "Remove a filter"),
            ("/filters", "List all filters"),
        ]),
        ("Welcome", "Admins", &[
            ("/setwelcome <msg>", "Set welcome message"),
            ("/resetwelcome", "Remove welcome message"),
            ("/welcome", "Preview welcome message"),
            ("/setwelcomedm <msg>", "Set DM to new members"),
            ("/setfarewell <msg>", "Set farewell message"),
            ("/farewell", "Preview farewell message"),
            ("/cleanwelcome", "Toggle auto-delete welcome"),
            ("/welcometest", "Test welcome with your name"),
        ]),
        ("Security", "Admins", &[
            ("/setflood <count>", "Set flood limit"),
            ("/flood", "Show flood settings"),
            ("/addswear <word>", "Add swear word"),
            ("/delswear <word>", "Remove swear word"),
        ]),
        ("Features", "Admins", &[
            ("/features", "List all features"),
            ("/enable <name>", "Enable a feature"),
            ("/disable <name>", "Disable a feature"),
            ("/toggle <name>", "Toggle a feature"),
            ("/featureinfo", "Feature details"),
            ("/myfeatures", "Your enabled features"),
            ("/resetfeatures", "Reset all features"),
            ("/enablecategory <cat>", "Enable a category"),
            ("/disablecategory <cat>", "Disable a category"),
        ]),
        ("Federation", "Admins", &[
            ("/newfed <name>", "Create a federation"),
            ("/joinfed <fed_id>", "Join group to federation"),
        ]),
    ];

    let mut text = String::new();
    text.push_str("*Nico Robin Bot \\— Command Reference*\n");
    text.push_str("_Reply to a user or pass @username to target them\\._\n\n");

    for (category, role, commands) in &sections {
        text.push_str(&format!("*{}* \\({}\\)\n", escape_md_v2(category), escape_md_v2(role)));
        for (cmd, desc) in *commands {
            text.push_str(&format!("{}  \\—  {}\n", escape_md_v2(cmd), escape_md_v2(desc)));
        }
        text.push('\n');
    }

    bot.send_message(msg.chat.id, text)
        .parse_mode(MarkdownV2)
        .await?;
    Ok(())
}
