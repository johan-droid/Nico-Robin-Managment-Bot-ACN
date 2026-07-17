use std::time::Duration;
use sqlx::postgres::PgPoolOptions;
use sqlx::{PgPool, Error};
use tracing::info;

pub async fn establish_connection(settings: &crate::config::Settings) -> Result<PgPool, Error> {
    let clean_url = settings.database_url_clean();
    
    info!(
        max_connections = settings.db_pool_size,
        connect_timeout_seconds = settings.db_connect_timeout,
        "initializing_database_connection_pool"
    );

    let pool = PgPoolOptions::new()
        .max_connections(settings.db_pool_size)
        .acquire_timeout(Duration::from_secs(settings.db_connect_timeout as u64))
        .max_lifetime(Duration::from_secs(settings.db_pool_recycle as u64))
        .connect(&clean_url)
        .await?;

    info!("database_connection_pool_established");
    Ok(pool)
}

pub async fn verify_database(pool: &PgPool) -> Result<(), Error> {
    sqlx::query("SELECT 1")
        .execute(pool)
        .await?;
    info!("database_ping_successful");
    Ok(())
}
