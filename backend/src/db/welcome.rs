use tokio_postgres::Client;

pub struct WelcomeSettings {
    pub welcome_message: Option<String>,
    pub farewell_message: Option<String>,
    pub welcome_dm_message: Option<String>,
    pub clean_welcome: bool,
}

/// Gets welcome settings for a group.
pub async fn get_welcome_settings(
    client: &Client,
    group_id: i64,
) -> Result<Option<WelcomeSettings>, String> {
    let row = client.query_opt(
        r#"SELECT welcome_message, farewell_message, welcome_dm_message, clean_welcome FROM welcome_settings WHERE group_id = $1"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;

    Ok(row.map(|r| WelcomeSettings {
        welcome_message: r.get(0),
        farewell_message: r.get(1),
        welcome_dm_message: r.get(2),
        clean_welcome: r.get(3),
    }))
}

/// Sets the welcome message for a group.
pub async fn set_welcome_message(
    client: &Client,
    group_id: i64,
    message: &str,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO welcome_settings (group_id, welcome_message) VALUES ($1, $2)
           ON CONFLICT (group_id) DO UPDATE SET welcome_message = $2, updated_at = NOW()"#,
        &[&group_id, &message]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Resets the welcome message for a group.
pub async fn reset_welcome_message(client: &Client, group_id: i64) -> Result<(), String> {
    client.execute(
        r#"UPDATE welcome_settings SET welcome_message = NULL, updated_at = NOW() WHERE group_id = $1"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Sets the farewell message for a group.
pub async fn set_farewell_message(
    client: &Client,
    group_id: i64,
    message: &str,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO welcome_settings (group_id, farewell_message) VALUES ($1, $2)
           ON CONFLICT (group_id) DO UPDATE SET farewell_message = $2, updated_at = NOW()"#,
        &[&group_id, &message]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Sets the DM welcome message for a group.
pub async fn set_welcome_dm_message(
    client: &Client,
    group_id: i64,
    message: &str,
) -> Result<(), String> {
    client.execute(
        r#"INSERT INTO welcome_settings (group_id, welcome_dm_message) VALUES ($1, $2)
           ON CONFLICT (group_id) DO UPDATE SET welcome_dm_message = $2, updated_at = NOW()"#,
        &[&group_id, &message]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(())
}

/// Toggles clean welcome for a group.
pub async fn toggle_clean_welcome(client: &Client, group_id: i64) -> Result<bool, String> {
    let row = client.query_one(
        r#"UPDATE welcome_settings SET clean_welcome = NOT clean_welcome, updated_at = NOW()
           WHERE group_id = $1 RETURNING clean_welcome"#,
        &[&group_id]
    )
    .await
    .map_err(|e| e.to_string())?;
    Ok(row.get(0))
}
