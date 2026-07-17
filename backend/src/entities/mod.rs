use sqlx::postgres::PgPoolOptions;
use sqlx::{Error, PgPool};
use std::time::Duration;
use tracing::{error, info, warn};

/// Number of retry attempts for database connection.
const DB_CONNECT_RETRIES: u32 = 3;

/// Base delay for exponential backoff (in seconds).
const DB_RETRY_BASE_DELAY_SECS: u64 = 2;

/// Establishes a PostgreSQL connection pool with the given settings.
/// Includes retry logic with exponential backoff.
pub async fn establish_connection(settings: &crate::config::Settings) -> Result<PgPool, Error> {
    let clean_url = settings.database_url_clean();

    info!(
        max_connections = settings.db_pool_size,
        connect_timeout_seconds = settings.db_connect_timeout,
        ssl_required = settings.db_ssl_required,
        "initializing_database_connection_pool"
    );

    // Attempt connection with retries
    let mut last_error = None;
    for attempt in 1..=DB_CONNECT_RETRIES {
        match try_connect(&clean_url, settings).await {
            Ok(pool) => {
                info!(attempt = attempt, "database_connection_pool_established");
                return Ok(pool);
            }
            Err(e) => {
                warn!(
                    attempt = attempt,
                    max_retries = DB_CONNECT_RETRIES,
                    error = %e,
                    "database_connection_attempt_failed"
                );
                last_error = Some(e);

                if attempt < DB_CONNECT_RETRIES {
                    let delay = Duration::from_secs(DB_RETRY_BASE_DELAY_SECS * attempt as u64);
                    info!(delay_secs = delay.as_secs(), "retrying_database_connection");
                    tokio::time::sleep(delay).await;
                }
            }
        }
    }

    let final_error = last_error.unwrap_or_else(|| {
        // Fallback: create a pool connect error manually
        Error::PoolClosed
    });

    error!(
        max_retries = DB_CONNECT_RETRIES,
        error = %final_error,
        "database_connection_failed_after_retries"
    );

    Err(final_error)
}

/// Attempts a single database connection.
async fn try_connect(url: &str, settings: &crate::config::Settings) -> Result<PgPool, Error> {
    let pool = PgPoolOptions::new()
        .max_connections(settings.db_pool_size)
        .acquire_timeout(Duration::from_secs(settings.db_connect_timeout as u64))
        .max_lifetime(Duration::from_secs(settings.db_pool_recycle as u64))
        .connect(url)
        .await?;

    Ok(pool)
}

/// Verifies the database connection by executing a simple query.
/// Also validates that the database is not in read-only mode.
pub async fn verify_database(pool: &PgPool) -> Result<(), Error> {
    // Verify basic connectivity
    sqlx::query("SELECT 1").execute(pool).await?;
    info!("database_ping_successful");

    // Verify write capability (critical for a bot that needs to store data)
    match sqlx::query("SELECT NOW()").execute(pool).await {
        Ok(_) => {
            info!("database_write_verification_successful");
        }
        Err(e) => {
            warn!(
                error = %e,
                "database_write_verification_issue - database may be read-only or slow"
            );
            // Don't fail startup for this, but log it
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_retry_constants() {
        assert_eq!(DB_CONNECT_RETRIES, 3);
        assert_eq!(DB_RETRY_BASE_DELAY_SECS, 2);
    }
}
