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

    // Upgrade to TLS (Hyperdrive requires TLS at the transport layer)
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
    let hyperdrive = env
        .hyperdrive("HYPERDRIVE")
        .map_err(|e| format!("Hyperdrive binding missing: {}", e))?;

    let host = hyperdrive.host();
    let port = hyperdrive.port();
    let user = hyperdrive.user();
    let password = hyperdrive.password();
    let database = hyperdrive.database();

    tracing::info!(host = %host, port = %port, db = %database, "connecting via hyperdrive socket");

    establish_connection_via_socket(&host, port, &user, &password, &database).await
}

// Note: Non-wasm32 uses its own connection logic in main.rs (native_main).