use serde_json::Value as JsonValue;
use tokio_postgres::Client;

pub struct UserProfile {
    pub user_id: i64,
    pub bio: String,
    pub data: JsonValue,
}

pub async fn get_or_create_profile(client: &Client, user_id: i64) -> Result<UserProfile, String> {
    let row = client
        .query_one(
            r#"WITH ins AS (
            INSERT INTO user_profiles (user_id) VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
        )
        SELECT user_id, bio, data FROM user_profiles WHERE user_id = $1"#,
            &[&user_id],
        )
        .await
        .map_err(|e| e.to_string())?;

    Ok(UserProfile {
        user_id: row.get(0),
        bio: crate::crypto::try_decrypt(&row.get::<_, String>(1)),
        data: row.get::<_, serde_json::Value>(2),
    })
}

/// Sets the bio for a user.
pub async fn set_bio(client: &Client, user_id: i64, bio: &str) -> Result<(), String> {
    let bio_enc = crate::crypto::try_encrypt(bio);
    client
        .execute(
            r#"INSERT INTO user_profiles (user_id, bio) VALUES ($1, $2)
           ON CONFLICT (user_id) DO UPDATE SET bio = $2, updated_at = NOW()"#,
            &[&user_id, &bio_enc],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// Deletes a user profile.
pub async fn delete_profile(client: &Client, user_id: i64) -> Result<bool, String> {
    let result = client
        .execute(
            r#"DELETE FROM user_profiles WHERE user_id = $1"#,
            &[&user_id],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(result > 0)
}
