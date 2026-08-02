use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use std::collections::HashMap;
use std::sync::Arc;
use std::sync::LazyLock;
use tokio::sync::Mutex;
use tokio_postgres::Client;

pub static ACTIVE_QUIZZES: LazyLock<Arc<Mutex<HashMap<i64, (String, u64)>>>> =
    LazyLock::new(|| Arc::new(Mutex::new(HashMap::new())));

pub async fn handle_quiz(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    match crate::db::games::get_random_quiz(client).await {
        Ok(Some((_id, question, answer))) => {
            let text = format!("Fufufu... Here is a question for you:\n\n{}\n\nReply to this message with your answer! First to answer correctly gets +10 Bounty. Wrong answers cost -5 Bounty.", question);
            let send_msg_result = bot
                .send_message(msg.chat.id, crate::utils::escape_md_v2(&text))
                .parse_mode(crate::telegram::ParseMode::MarkdownV2)
                .await;

            if let Ok(sent) = send_msg_result {
                let mut guard = ACTIVE_QUIZZES.lock().await;
                guard.insert(msg.chat.id, (answer, sent.message_id));
            }
        }
        Ok(None) => {
            let text = "Fufufu... It seems I don't have any questions right now.";
            let _ = bot.send_message(msg.chat.id, text).await;
        }
        Err(e) => {
            tracing::error!("Error fetching quiz: {}", e);
            let text = "Fufufu... The Robin Quiz feature is currently being studied by the scholars of Ohara.";
            let _ = bot.send_message(msg.chat.id, text).await;
        }
    }
    Ok(())
}
