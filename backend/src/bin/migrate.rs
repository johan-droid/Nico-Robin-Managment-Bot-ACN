use std::env;
use std::fs;
use native_tls::TlsConnector;
use postgres_native_tls::MakeTlsConnector;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::from_filename(".env.local").ok();
    dotenvy::dotenv().ok();

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set in env");
    println!("Connecting to database for migrations...");

    let native_tls_connector = TlsConnector::builder().build()?;
    let connector = MakeTlsConnector::new(native_tls_connector);

    let (client, connection) = tokio_postgres::connect(&database_url, connector).await?;

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("Database connection error: {}", e);
        }
    });

    println!("Connected successfully. Dropping stale tables to ensure clean schema update...");
    let drop_query = "
        DROP TABLE IF EXISTS feature_flags, warnings, welcome_settings, welcome_messages, 
                            swears, flood, federations, groups, notes, filters, user_profiles CASCADE;
    ";
    if let Err(e) = client.batch_execute(drop_query).await {
        println!("Warning while dropping old tables: {}", e);
    }

    println!("Applying migrations from migrations/ directory...");

    let mut entries = fs::read_dir("migrations")?
        .filter_map(|res| res.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map_or(false, |ext| ext == "sql"))
        .collect::<Vec<_>>();

    // Sort by name so migrations execute in alphabetical prefix order (001, 002...)
    entries.sort();

    for path in entries {
        let filename = path.file_name().unwrap().to_string_lossy().into_owned();
        println!("Running migration {}...", filename);
        let sql = fs::read_to_string(&path)?;
        client.batch_execute(&sql).await?;
    }

    println!("All migrations applied successfully!");
    Ok(())
}
