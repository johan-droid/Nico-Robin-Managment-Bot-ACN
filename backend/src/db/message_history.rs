use tokio_postgres::Client;

/// Maximum number of messages kept per chat in `message_history`.
pub const HISTORY_MAX_PER_CHAT: i64 = 500;

/// A single stored message used for quote rendering.
#[derive(Clone, Debug)]
pub struct HistoryMessage {
    pub message_id: u64,
    pub user_id: u64,
    pub user_name: String,
    pub text: String,
    pub date: u64,
}

/// Records a message into persistent history. Idempotent on `(chat_id, message_id)`.
pub async fn record_message(
    client: &Client,
    chat_id: i64,
    message_id: u64,
    user_id: u64,
    user_name: &str,
    text: &str,
    date: u64,
) -> Result<(), String> {
    let name_enc = crate::crypto::try_encrypt(user_name);
    let text_enc = crate::crypto::try_encrypt(text);
    client
        .execute(
            "INSERT INTO message_history (chat_id, message_id, user_id, user_name, text, date) \
             VALUES ($1, $2, $3, $4, $5, $6) \
             ON CONFLICT (chat_id, message_id) DO NOTHING",
            &[
                &chat_id,
                &(message_id as i64),
                &(user_id as i64),
                &name_enc,
                &text_enc,
                &(date as i64),
            ],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Returns the most recent `limit` messages for a chat in chronological order.
pub async fn get_recent(
    client: &Client,
    chat_id: i64,
    limit: usize,
) -> Result<Vec<HistoryMessage>, String> {
    let rows = client
        .query(
            "SELECT message_id, user_id, user_name, text, date \
             FROM message_history WHERE chat_id = $1 \
             ORDER BY date DESC, id DESC LIMIT $2",
            &[&chat_id, &(limit as i64)],
        )
        .await
        .map_err(|e| e.to_string())?;

    let mut messages: Vec<HistoryMessage> = rows
        .iter()
        .map(|r| HistoryMessage {
            message_id: r.get::<_, i64>(0) as u64,
            user_id: r.get::<_, i64>(1) as u64,
            user_name: crate::crypto::try_decrypt(&r.get::<_, String>(2)),
            text: crate::crypto::try_decrypt(&r.get::<_, String>(3)),
            date: r.get::<_, i64>(4) as u64,
        })
        .collect();

    messages.reverse();
    Ok(messages)
}

/// Returns messages between two message IDs (inclusive) for a chat, in ascending order.
pub async fn get_recent_between(
    client: &Client,
    chat_id: i64,
    from_id: u64,
    to_id: u64,
) -> Result<Vec<HistoryMessage>, String> {
    let rows = client
        .query(
            "SELECT message_id, user_id, user_name, text, date \
             FROM message_history WHERE chat_id = $1 AND message_id >= $2 AND message_id <= $3 \
             ORDER BY message_id ASC LIMIT 500",
            &[&chat_id, &(from_id as i64), &(to_id as i64)],
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(rows
        .iter()
        .map(|r| HistoryMessage {
            message_id: r.get::<_, i64>(0) as u64,
            user_id: r.get::<_, i64>(1) as u64,
            user_name: crate::crypto::try_decrypt(&r.get::<_, String>(2)),
            text: crate::crypto::try_decrypt(&r.get::<_, String>(3)),
            date: r.get::<_, i64>(4) as u64,
        })
        .collect())
}

/// Deletes all but the newest `keep` messages for a chat.
pub async fn prune_old(client: &Client, chat_id: i64, keep: i64) -> Result<(), String> {
    client
        .execute(
            "DELETE FROM message_history mh \
             WHERE mh.chat_id = $1 AND mh.id < (
                 SELECT id FROM message_history
                 WHERE chat_id = $1
                 ORDER BY date DESC, id DESC
                 LIMIT 1 OFFSET $2
             )",
            &[&chat_id, &keep],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}
