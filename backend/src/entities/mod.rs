#[cfg(target_arch = "wasm32")]
pub async fn establish_connection(env: &worker::Env) -> Result<tokio_postgres::Client, String> {
    let hyperdrive = env
        .hyperdrive("HYPERDRIVE")
        .map_err(|e| format!("Hyperdrive binding missing: {}", e))?;

    let connection_string = hyperdrive.connection_string();
    tracing::info!("establishing hyperdrive tokio_postgres connection via socket");

    let (client, connection) = tokio_postgres::connect(&connection_string, tokio_postgres::NoTls)
        .await
        .map_err(|e| format!("Connection error: {}", e))?;

    wasm_bindgen_futures::spawn_local(async move {
        if let Err(e) = connection.await {
            eprintln!("Connection error: {}", e);
        }
    });

    Ok(client)
}