use crate::telegram::native_api::Bot;
use std::sync::Arc;
use tokio::time::{sleep, Duration};
use tokio_postgres::Client;

pub fn start_cleanup_task(client: Arc<Client>, _bot: Bot) {
    tokio::spawn(async move {
        loop {
            // Run every hour
            sleep(Duration::from_secs(3600)).await;

            // Delete expired temp_mutes
            if let Ok(expired_mutes) = crate::db::moderation::get_expired_temp_mutes(&client).await
            {
                for (group_id, user_id) in expired_mutes {
                    let _ =
                        crate::db::moderation::remove_temp_mute(&client, group_id, user_id).await;
                    // Note: Telegram automatically un-restricts the user when the time expires,
                    // so we only need to clean up our local database tracking.
                }
            }

            // Delete expired temp_bans
            if let Ok(expired_bans) = crate::db::moderation::get_expired_temp_bans(&client).await {
                for (group_id, user_id) in expired_bans {
                    let _ =
                        crate::db::moderation::remove_temp_ban(&client, group_id, user_id).await;
                    // Telegram auto-unbans on expiration, so we just clean DB.
                }
            }
        }
    });
}
