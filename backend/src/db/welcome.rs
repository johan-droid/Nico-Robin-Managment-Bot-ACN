use sqlx::PgPool;

pub struct WelcomeSettings {
    pub welcome_message: Option<String>,
    pub farewell_message: Option<String>,
    pub welcome_dm_message: Option<String>,
    pub clean_welcome: bool,
}

type WelcomeRow = (Option<String>, Option<String>, Option<String>, bool);

/// Gets welcome settings for a group.
pub async fn get_welcome_settings(
    pool: &PgPool,
    group_id: i64,
) -> Result<Option<WelcomeSettings>, sqlx::Error> {
    let row: Option<WelcomeRow> =
        sqlx::query_as(
            r#"SELECT welcome_message, farewell_message, welcome_dm_message, clean_welcome FROM welcome_settings WHERE group_id = $1"#,
        )
        .bind(group_id)
        .fetch_optional(pool)
        .await?;
    Ok(row.map(|r| WelcomeSettings {
        welcome_message: r.0,
        farewell_message: r.1,
        welcome_dm_message: r.2,
        clean_welcome: r.3,
    }))
}

/// Sets the welcome message for a group.
pub async fn set_welcome_message(
    pool: &PgPool,
    group_id: i64,
    message: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO welcome_settings (group_id, welcome_message) VALUES ($1, $2)
           ON CONFLICT (group_id) DO UPDATE SET welcome_message = $2, updated_at = NOW()"#,
    )
    .bind(group_id)
    .bind(message)
    .execute(pool)
    .await?;
    Ok(())
}

/// Resets the welcome message for a group.
pub async fn reset_welcome_message(pool: &PgPool, group_id: i64) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"UPDATE welcome_settings SET welcome_message = NULL, updated_at = NOW() WHERE group_id = $1"#,
    )
    .bind(group_id)
    .execute(pool)
    .await?;
    Ok(())
}

/// Sets the farewell message for a group.
pub async fn set_farewell_message(
    pool: &PgPool,
    group_id: i64,
    message: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO welcome_settings (group_id, farewell_message) VALUES ($1, $2)
           ON CONFLICT (group_id) DO UPDATE SET farewell_message = $2, updated_at = NOW()"#,
    )
    .bind(group_id)
    .bind(message)
    .execute(pool)
    .await?;
    Ok(())
}

/// Sets the DM welcome message for a group.
pub async fn set_welcome_dm_message(
    pool: &PgPool,
    group_id: i64,
    message: &str,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO welcome_settings (group_id, welcome_dm_message) VALUES ($1, $2)
           ON CONFLICT (group_id) DO UPDATE SET welcome_dm_message = $2, updated_at = NOW()"#,
    )
    .bind(group_id)
    .bind(message)
    .execute(pool)
    .await?;
    Ok(())
}

/// Toggles clean welcome for a group.
pub async fn toggle_clean_welcome(pool: &PgPool, group_id: i64) -> Result<bool, sqlx::Error> {
    let row: (bool,) = sqlx::query_as(
        r#"UPDATE welcome_settings SET clean_welcome = NOT clean_welcome, updated_at = NOW()
           WHERE group_id = $1 RETURNING clean_welcome"#,
    )
    .bind(group_id)
    .fetch_one(pool)
    .await?;
    Ok(row.0)
}
