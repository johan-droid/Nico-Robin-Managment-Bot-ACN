use tokio_postgres::Client;

/// Idempotent startup backfill for rows written while encryption was disabled.
///
/// When ENCRYPTION_KEY is enabled after plaintext data already exists, the
/// `*_hash` columns of legacy rows are NULL, so hash-based lookups miss them
/// (get_note / check_filter / check_swear / username resolution all key on the
/// hash once crypto is active). This routine hashes those legacy rows.
///
/// `try_decrypt` returns ciphertext-decrypted values OR passes plaintext through
/// unchanged, so it covers both a legacy plaintext row and a legacy encrypted
/// row whose hash column was never populated. Rows that already carry a hash are
/// untouched, making the whole pass re-runnable.
pub async fn backfill_legacy_hashes(client: &Client) -> Result<usize, String> {
    let crypto = match crate::crypto::try_crypto() {
        Some(c) => c,
        None => return Ok(0),
    };

    let mut total: usize = 0;

    for (table, column) in [
        ("notes", "name"),
        ("filters", "trigger_text"),
        ("swear_words", "word"),
    ] {
        let rows = client
            .query(
                &format!("SELECT id, {} FROM {} WHERE {}_hash IS NULL", column, table, column),
                &[],
            )
            .await
            .map_err(|e| format!("Backfill scan on {} failed: {}", table, e))?;

        for row in rows {
            let id: i32 = row.get(0);
            let value: String = row.get(1);
            let plain = crate::crypto::try_decrypt(&value);
            let hash = crypto.hash_text(&plain);
            let hash_col = format!("{}_hash", column);
            let affected = client
                .execute(
                    &format!("UPDATE {} SET {} = $1 WHERE id = $2", table, hash_col),
                    &[&hash, &id],
                )
                .await
                .map_err(|e| format!("Backfill update on {} failed: {}", table, e))?;
            total += affected as usize;
        }
    }

    // username_cache uses the same id PK and username_hash column.
    let rows = client
        .query(
            "SELECT id, username FROM username_cache WHERE username_hash IS NULL",
            &[],
        )
        .await
        .map_err(|e| format!("Backfill scan on username_cache failed: {}", e))?;

    for row in rows {
        let id: i32 = row.get(0);
        let value: String = row.get(1);
        let plain = crate::crypto::try_decrypt(&value);
        let hash = crypto.hash_text(&plain);
        let affected = client
            .execute(
                "UPDATE username_cache SET username_hash = $1 WHERE id = $2",
                &[&hash, &id],
            )
            .await
            .map_err(|e| format!("Backfill update on username_cache failed: {}", e))?;
        total += affected as usize;
    }

    Ok(total)
}
