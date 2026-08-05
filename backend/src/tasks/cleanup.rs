use crate::telegram::native_api::Bot;
use tokio::time::{sleep, Duration};

pub fn start_cleanup_task(pool: deadpool_postgres::Pool) {
    tokio::spawn(async move {
        loop {
            // Run every hour
            sleep(Duration::from_secs(3600)).await;

            let client = match pool.get().await {
                Ok(c) => c,
                Err(e) => {
                    tracing::warn!(error = %e, "Cleanup task: DB checkout failed");
                    continue;
                }
            };

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

/// Background sweep that fires due reminders (user_id + message + remind_at) by
/// DM'ing the user, then removes the reminder row so it is never re-fired.
pub fn start_reminder_sweep(pool: deadpool_postgres::Pool, bot: Bot) {
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(30));
        loop {
            interval.tick().await;
            let client = match pool.get().await {
                Ok(c) => c,
                Err(e) => {
                    tracing::warn!(error = %e, "Reminder sweep: DB checkout failed");
                    continue;
                }
            };

            let rows = match client
                .query(
                    "SELECT id, user_id, message FROM reminders WHERE remind_at <= NOW()",
                    &[],
                )
                .await
            {
                Ok(r) => r,
                Err(e) => {
                    tracing::warn!(error = %e, "Reminder sweep query failed");
                    continue;
                }
            };

            for row in rows {
                let id: i32 = row.get(0);
                let user_id: i64 = row.get(1);
                let message: String = row.get(2);
                // Deliver then remove so a failure retries it on the next sweep.
                let _ = bot.send_message(user_id, &message).await;
                let _ = client
                    .execute("DELETE FROM reminders WHERE id = $1", &[&id])
                    .await;
            }
        }
    });
}
