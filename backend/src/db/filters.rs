use sqlx::PgPool;

pub struct Filter {
    pub trigger_text: String,
    pub response: String,
}

pub async fn add_filter(
    pool: &PgPool,
    group_id: i64,
    trigger_text: &str,
    response: &str,
    created_by: i64,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO filters (group_id, trigger_text, response, created_by)
           VALUES ($1, $2, $3, $4)
           ON CONFLICT (group_id, trigger_text) DO UPDATE SET response = $3"#,
    )
    .bind(group_id)
    .bind(trigger_text)
    .bind(response)
    .bind(created_by)
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn list_filters(pool: &PgPool, group_id: i64) -> Result<Vec<Filter>, sqlx::Error> {
    let rows: Vec<(String, String)> = sqlx::query_as(
        r#"SELECT trigger_text, response FROM filters WHERE group_id = $1 ORDER BY trigger_text"#,
    )
    .bind(group_id)
    .fetch_all(pool)
    .await?;
    Ok(rows
        .into_iter()
        .map(|(trigger_text, response)| Filter {
            trigger_text,
            response,
        })
        .collect())
}

pub async fn remove_filter(
    pool: &PgPool,
    group_id: i64,
    trigger_text: &str,
) -> Result<bool, sqlx::Error> {
    let result = sqlx::query(r#"DELETE FROM filters WHERE group_id = $1 AND trigger_text = $2"#)
        .bind(group_id)
        .bind(trigger_text)
        .execute(pool)
        .await?;
    Ok(result.rows_affected() > 0)
}
