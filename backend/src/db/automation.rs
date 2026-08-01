use tokio_postgres::Client;

pub async fn get_due_jobs(client: &Client) -> Result<Vec<(i32, String)>, String> {
    let rows = client
        .query(
            "SELECT id, job_type FROM scheduled_jobs WHERE run_at <= NOW()",
            &[],
        )
        .await
        .map_err(|e| e.to_string())?;
    Ok(rows.iter().map(|r| (r.get(0), r.get(1))).collect())
}
