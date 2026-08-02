use tokio_postgres::Client;
use crate::telegram::api::Bot;
use crate::telegram::update::Message;

pub async fn handle_quiz(bot: Bot, msg: Message, _client: &Client) -> Result<(), String> {
    let text = "Fufufu... The Robin Quiz feature is currently being studied by the scholars of Ohara. I will ask you questions to test your knowledge soon!";
    let _ = bot.send_message(msg.chat.id, text).await;
    Ok(())
}
