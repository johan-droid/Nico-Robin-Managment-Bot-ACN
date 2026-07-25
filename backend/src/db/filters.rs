use tokio_postgres::Client;

pub struct Filter {
    pub trigger_text: String,
    pub response: String,
}

pub async fn add_filter(
    client: &Client,
    group_id: i64,
    trigger_text: &str,
    response: &str,
    created_by: i64,
) -> Result<(), String> {
    client
        .execute(
            r#"INSERT INTO filters (group_id, trigger_text, response, created_by)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id, trigger_text) DO UPDATE SET response = $3"#,
            &[&group_id, &trigger_text, &response, &created_by],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub async fn list_filters(client: &Client, group_id: i64) -> Result<Vec<Filter>, String> {
    let rows = client.query(
        r#"SELECT trigger_text, response FROM filters WHERE group_id = $1 ORDER BY trigger_text"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;

    Ok(rows
        .into_iter()
        .map(|row| Filter {
            trigger_text: row.get(0),
            response: row.get(1),
        })
        .collect())
}

pub async fn remove_filter(
    client: &Client,
    group_id: i64,
    trigger_text: &str,
) -> Result<bool, String> {
    let result = client
        .execute(
            r#"DELETE FROM filters WHERE group_id = $1 AND trigger_text = $2"#,
            &[&group_id, &trigger_text],
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(result > 0)
}
