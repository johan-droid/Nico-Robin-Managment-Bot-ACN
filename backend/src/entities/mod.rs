use tokio_postgres::Client;
use tokio_postgres::config::Config;
use tokio_postgres::tls::NoTls;

#[cfg(target_arch = "wasm32")]
pub async fn establish_connection_via_socket(
    host: &str,
    port: u16,
    user: &str,
    password: &str,
    database: &str,
) -> Result<Client, String> {
    use worker::SecureTransport;

    let socket = worker::Socket::builder()
        .secure_transport(SecureTransport::StartTls)
        .connect(host, port)
        .map_err(|e| format!("Socket connect error: {}", e))?;

    // Upgrade to TLS
    let tls_socket = socket.start_tls();

    let mut config = Config::new();
    config.user(user);
    config.password(password.as_bytes());
    config.dbname(database);

    let (client, connection) = config
        .connect_raw(tls_socket, NoTls)
        .await
        .map_err(|e| format!("Connection error: {}", e))?;

    wasm_bindgen_futures::spawn_local(async move {
        if let Err(e) = connection.await {
            eprintln!("Connection error: {}", e);
        }
    });

    Ok(client)
}

#[cfg(target_arch = "wasm32")]
pub async fn establish_connection(env: &worker::Env) -> Result<Client, String> {
    if let Ok(hyperdrive) = env.hyperdrive("HYPERDRIVE") {
        let host = hyperdrive.host();
        if !host.is_empty() && !host.contains("dummy") && !host.contains("replace") && !host.contains("localhost") {
            let port = hyperdrive.port();
            let user = hyperdrive.user();
            let password = hyperdrive.password();
            let database = hyperdrive.database();

            tracing::info!(host = %host, port = %port, db = %database, "connecting via hyperdrive socket");
            if let Ok(client) = establish_connection_via_socket(&host, port, &user, &password, &database).await {
                return Ok(client);
            }
        }
    }

    let db_url = env
        .var("DATABASE_URL")
        .map_err(|_| "DATABASE_URL environment variable is missing".to_string())?
        .to_string();

    let parsed = url::Url::parse(&db_url).map_err(|e| format!("Invalid DATABASE_URL: {}", e))?;
    let host = parsed.host_str().ok_or("Missing host in DATABASE_URL")?;
    let port = parsed.port().unwrap_or(5432);
    let user = parsed.username();
    let password = parsed.password().unwrap_or("");
    let database = parsed.path().trim_start_matches('/');

    tracing::info!(host = %host, port = %port, db = %database, "connecting via direct socket using DATABASE_URL");

    establish_connection_via_socket(host, port, user, password, database).await
}