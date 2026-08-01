use std::env;
use std::fs;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::from_filename(".env.local").ok();
    dotenvy::dotenv().ok();

    let args: Vec<String> = env::args().collect();
    let reset = args.iter().any(|a| a == "--reset");

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set in env");
    println!("Connecting to database for migrations...");

    rustls::crypto::ring::default_provider()
        .install_default()
        .ok();
    let mut root_store = rustls::RootCertStore::empty();
    root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());
    let rustls_config = rustls::ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
    let connector = tokio_postgres_rustls::MakeRustlsConnect::new(rustls_config);

    let (client, connection) = tokio_postgres::connect(&database_url, connector).await?;

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("Database connection error: {}", e);
        }
    });

    if reset {
        println!("--reset: Dropping stale tables to ensure clean schema...");
        let drop_query = "
            DROP TABLE IF EXISTS feature_flags, warnings, welcome_settings,
                                swears, flood_settings, federations, groups, notes, filters, user_profiles,
                                username_cache, group_rules, group_locks, gbans CASCADE;
        ";
        if let Err(e) = client.batch_execute(drop_query).await {
            println!("Warning while dropping old tables: {}", e);
        }
    } else {
        println!("--apply-only mode: preserving existing data, only applying new migrations");
    }

    // Ensure the migrations tracking table exists
    let _ = client
        .batch_execute(
            "CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );",
        )
        .await;

    println!("Applying migrations from migrations/ directory...");

    let mut entries = fs::read_dir("migrations")?
        .filter_map(|res| res.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|ext| ext == "sql"))
        .collect::<Vec<_>>();

    // Sort by name so migrations execute in alphabetical prefix order (001, 002...)
    entries.sort();

    for path in entries {
        let filename = path.file_name().unwrap().to_string_lossy().into_owned();

        // Skip already-applied migrations (unless --reset was used)
        if !reset {
            let already_applied: bool = client
                .query_one(
                    "SELECT EXISTS(SELECT 1 FROM _migrations WHERE name = $1)",
                    &[&filename],
                )
                .await?
                .get(0);
            if already_applied {
                println!("  Skipping {} (already applied)", filename);
                continue;
            }
        }

        println!("  Running {}...", filename);
        let sql = fs::read_to_string(&path)?;
        client.batch_execute(&sql).await?;

        // Record as applied
        let _ = client
            .execute(
                "INSERT INTO _migrations (name) VALUES ($1) ON CONFLICT (name) DO NOTHING",
                &[&filename],
            )
            .await;
    }

    println!("All migrations applied successfully!");
    Ok(())
}
