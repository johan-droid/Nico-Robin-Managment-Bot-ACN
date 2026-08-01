use std::env;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

#[derive(Clone)]
struct CustomTlsConnect {
    inner: tokio_postgres_rustls::MakeRustlsConnect,
    domain: String,
}

impl<S> tokio_postgres::tls::MakeTlsConnect<S> for CustomTlsConnect
where
    tokio_postgres_rustls::MakeRustlsConnect: tokio_postgres::tls::MakeTlsConnect<S>,
{
    type Stream = <tokio_postgres_rustls::MakeRustlsConnect as tokio_postgres::tls::MakeTlsConnect<S>>::Stream;
    type TlsConnect = <tokio_postgres_rustls::MakeRustlsConnect as tokio_postgres::tls::MakeTlsConnect<S>>::TlsConnect;
    type Error = <tokio_postgres_rustls::MakeRustlsConnect as tokio_postgres::tls::MakeTlsConnect<S>>::Error;

    fn make_tls_connect(&mut self, _domain: &str) -> Result<Self::TlsConnect, Self::Error> {
        self.inner.make_tls_connect(&self.domain)
    }
}

fn find_migrations_dir() -> Result<PathBuf, io::Error> {
    if let Ok(dir) = env::var("MIGRATIONS_PATH") {
        if !dir.trim().is_empty() {
            return Ok(PathBuf::from(dir));
        }
    }
    for candidate in ["migrations", "backend/migrations"] {
        let path = Path::new(candidate);
        if path.is_dir() {
            return Ok(path.to_path_buf());
        }
    }
    Err(io::Error::new(
        io::ErrorKind::NotFound,
        "migrations directory not found (looked for 'migrations' and 'backend/migrations')",
    ))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    dotenvy::from_filename(".env.local").ok();
    dotenvy::dotenv().ok();

    let args: Vec<String> = env::args().collect();
    let reset = args.iter().any(|a| a == "--reset");

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set in env");
    
    // Bypass tokio-postgres IPv6 bug on Render by forcing IPv4 resolution manually
    let mut parsed_url = url::Url::parse(&database_url).expect("Invalid DATABASE_URL");
    
    // Remove channel_binding from connection URL as Neon PgBouncer pooler does not support it
    let pairs: Vec<_> = parsed_url.query_pairs().into_owned().filter(|(k, _)| k != "channel_binding").collect();
    parsed_url.query_pairs_mut().clear().extend_pairs(pairs.into_iter());
    
    let original_host = parsed_url.host_str().expect("DATABASE_URL must have a host").to_string();
    
    println!("Resolving database host {} to IPv4...", original_host);
    let mut ipv4_addr = None;
    if let Ok(addrs) = tokio::net::lookup_host((original_host.as_str(), parsed_url.port().unwrap_or(5432))).await {
        for addr in addrs {
            if addr.is_ipv4() {
                ipv4_addr = Some(addr.ip().to_string());
                break;
            }
        }
    }
    
    let ipv4_str = ipv4_addr.expect("No IPv4 address found for DB host");
    println!("Resolved to IPv4: {}", ipv4_str);
    parsed_url.set_host(Some(&ipv4_str)).unwrap();
    let ipv4_database_url = parsed_url.to_string();

    println!("Connecting to database for migrations...");

    rustls::crypto::ring::default_provider()
        .install_default()
        .ok();
    let mut root_store = rustls::RootCertStore::empty();
    root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());
    let rustls_config = rustls::ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
        
    let connector = CustomTlsConnect {
        inner: tokio_postgres_rustls::MakeRustlsConnect::new(rustls_config),
        domain: original_host,
    };

    let (client, connection) = tokio_postgres::connect(&ipv4_database_url, connector).await?;

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

    let migrations_dir = find_migrations_dir()?;

    let mut entries = fs::read_dir(&migrations_dir)?
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
