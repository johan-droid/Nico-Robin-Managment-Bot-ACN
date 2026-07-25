use tokio_postgres::Client;

pub async fn add_swear(client: &Client, group_id: i64, word: &str) -> Result<(), String> {
    let lower = word.to_lowercase();
    client
        .execute(
            r#"INSERT INTO swear_words (group_id, word) VALUES ($1, $2)
           ON CONFLICT (group_id, word) DO NOTHING"#,
            &[&group_id, &lower],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn remove_swear(client: &Client, group_id: i64, word: &str) -> Result<bool, String> {
    let lower = word.to_lowercase();
    let result = client
        .execute(
            r#"DELETE FROM swear_words WHERE group_id = $1 AND word = $2"#,
            &[&group_id, &lower],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(result > 0)
}
