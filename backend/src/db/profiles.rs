use sqlx::PgPool;
use serde_json::Value as JsonValue;

pub struct UserProfile {
    pub user_id: i64,
    pub bio: String,
    pub data: JsonValue,
}

pub async fn get_or_create_profile(
    pool: &PgPool,
    user_id: i64,
) -> Result<UserProfile, sqlx::Error> {
    let row: (i64, String, JsonValue) = sqlx::query_as(
        r#"WITH ins AS (
            INSERT INTO user_profiles (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
        )
        SELECT user_id, bio, data FROM user_profiles WHERE user_id = $1"#,
    )
    .bind(user_id)
    .fetch_one(pool)
    .await?;
    Ok(UserProfile {
        user_id: row.0,
        bio: row.1,
        data: row.2,
    })
}

/// Sets the bio for a user.
pub async fn set_bio(pool: &PgPool, user_id: i64, bio: &str) -> Result<(), sqlx::Error> {
    sqlx::query(
        r#"INSERT INTO user_profiles (user_id, bio) VALUES ($1, $2)
           ON CONFLICT (user_id) DO UPDATE SET bio = $2, updated_at = NOW()"#,
    )
    .bind(user_id)
    .bind(bio)
    .execute(pool)
    .await?;
    Ok(())
}

/// Deletes a user profile.
pub async fn delete_profile(pool: &PgPool, user_id: i64) -> Result<bool, sqlx::Error> {
    let result = sqlx::query(r#"DELETE FROM user_profiles WHERE user_id = $1"#)
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(result.rows_affected() > 0)
}
