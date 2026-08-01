use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;
use tokio_postgres::NoTls;

#[tokio::main(flavor = "current_thread")]
async fn main() {
    dotenvy::from_filename(".env.local").ok();
    dotenvy::dotenv().ok();

    println!("Starting local development diagnostic check...");

    let mut report = String::new();
    report.push_str("# Nico Robin Bot - Local Diagnostic Report\n\n");

    // 1. Git Information
    report.push_str("## Git Status\n");
    let git_branch = Command::new("git")
        .args(["rev-parse", "--abbrev-ref", "HEAD"])
        .output()
        .ok()
        .and_then(|out| String::from_utf8(out.stdout).ok())
        .unwrap_or_else(|| "Unknown".to_string());
    let git_branch = git_branch.trim();

    let git_commit = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .ok()
        .and_then(|out| String::from_utf8(out.stdout).ok())
        .unwrap_or_else(|| "Unknown".to_string());
    let git_commit = git_commit.trim();

    let git_status = Command::new("git")
        .args(["status", "--porcelain"])
        .output()
        .ok()
        .and_then(|out| String::from_utf8(out.stdout).ok())
        .unwrap_or_default();
    let git_status = git_status.trim();
    let is_dirty = !git_status.is_empty();

    report.push_str(&format!("- **Branch**: {}\n", git_branch));
    report.push_str(&format!("- **Commit**: {}\n", git_commit));
    report.push_str(&format!(
        "- **Dirty Status**: {}\n",
        if is_dirty {
            "Yes (uncommitted changes present)"
        } else {
            "No (clean)"
        }
    ));
    if is_dirty {
        report.push_str("```\n");
        report.push_str(git_status);
        report.push_str("\n```\n");
    }
    report.push('\n');

    // 2. Runtime Information
    report.push_str("## Runtime Information\n");
    let rustc_version = Command::new("rustc")
        .arg("--version")
        .output()
        .ok()
        .and_then(|out| String::from_utf8(out.stdout).ok())
        .unwrap_or_else(|| "Unknown".to_string());
    let rustc_version = rustc_version.trim();

    report.push_str(&format!("- **Rustc Version**: {}\n", rustc_version));
    report.push_str(&format!(
        "- **Application Version**: {}\n",
        env!("CARGO_PKG_VERSION")
    ));
    report.push('\n');

    // 3. Configuration Check
    report.push_str("## Environment Configuration Validity\n");
    let required_vars = [
        "BOT_TOKEN",
        "DATABASE_URL",
        "SUDO_USERS",
        "WEBHOOK_SECRET_PATH",
        "PORT",
        "SENTRY_DSN",
    ];

    let mut config_ok = true;
    for var in required_vars {
        match env::var(var) {
            Ok(val) => {
                let status = if val.is_empty() {
                    config_ok = false;
                    "❌ Present but Empty"
                } else {
                    "✅ Present (Redacted)"
                };
                report.push_str(&format!("- **{}**: {}\n", var, status));
            }
            Err(_) => {
                config_ok = false;
                report.push_str(&format!("- **{}**: ❌ Missing\n", var));
            }
        }
    }
    report.push('\n');

    // 4. Database Connectivity
    report.push_str("## Database Connectivity\n");
    let db_url = env::var("DATABASE_URL").ok();
    if let Some(url) = db_url {
        if url.is_empty() {
            report.push_str("- **Status**: ❌ Database URL is empty\n");
        } else {
            // Attempt to connect
            let connector = if url.contains("sslmode=require")
                || env::var("DB_SSL_REQUIRED").unwrap_or_default() == "true"
            {
                rustls::crypto::ring::default_provider()
                    .install_default()
                    .ok();
                let mut root_store = rustls::RootCertStore::empty();
                root_store.extend(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());
                let rustls_config = rustls::ClientConfig::builder()
                    .with_root_certificates(root_store)
                    .with_no_client_auth();
                let make_connector = tokio_postgres_rustls::MakeRustlsConnect::new(rustls_config);
                ConnectMode::Tls(make_connector)
            } else {
                ConnectMode::NoTls
            };

            match connector {
                ConnectMode::Tls(conn) => {
                    match tokio_postgres::connect(&url, conn).await {
                        Ok((client, connection)) => {
                            tokio::spawn(async move {
                                let _ = connection.await;
                            });
                            match client.execute("SELECT 1", &[]).await {
                                Ok(_) => report.push_str("- **Status**: ✅ Connected successfully (TLS)\n"),
                                Err(e) => report.push_str(&format!("- **Status**: ❌ Connection established but query failed: {}\n", e)),
                            }
                        }
                        Err(e) => report.push_str(&format!(
                            "- **Status**: ❌ Failed to connect (TLS): {}\n",
                            e
                        )),
                    }
                }
                ConnectMode::NoTls => {
                    match tokio_postgres::connect(&url, NoTls).await {
                        Ok((client, connection)) => {
                            tokio::spawn(async move {
                                let _ = connection.await;
                            });
                            match client.execute("SELECT 1", &[]).await {
                                Ok(_) => report.push_str("- **Status**: ✅ Connected successfully (No TLS)\n"),
                                Err(e) => report.push_str(&format!("- **Status**: ❌ Connection established but query failed: {}\n", e)),
                            }
                        }
                        Err(e) => report.push_str(&format!(
                            "- **Status**: ❌ Failed to connect (No TLS): {}\n",
                            e
                        )),
                    }
                }
                ConnectMode::Error(err) => {
                    report.push_str(&format!("- **Status**: ❌ Connector error: {}\n", err));
                }
            }
        }
    } else {
        report.push_str("- **Status**: ❌ DATABASE_URL env var missing\n");
    }
    report.push('\n');

    // 5. Diagnostics Directory Status
    report.push_str("## Recent Crash and Failure Reports\n");
    let crash_count = count_reports("diagnostics/crashes");
    let failure_count = count_reports("diagnostics/failures");

    report.push_str(&format!(
        "- **Unhandled Crashes (diagnostics/crashes/)**: {}\n",
        crash_count
    ));
    report.push_str(&format!(
        "- **Centralized Failures (diagnostics/failures/)**: {}\n",
        failure_count
    ));
    report.push('\n');

    // Save report to file
    let report_path = "diagnostic-report.md";
    match fs::write(report_path, &report) {
        Ok(_) => println!("Diagnostic report written successfully to {}", report_path),
        Err(e) => eprintln!("Failed to write diagnostic report: {}", e),
    }

    println!("--------------------------------------------------");
    println!("{}", report);
    println!("--------------------------------------------------");

    if config_ok {
        println!("Diagnostic completed successfully. Environment is valid.");
    } else {
        println!("Diagnostic completed with errors. Please check the report above.");
    }
}

enum ConnectMode {
    Tls(tokio_postgres_rustls::MakeRustlsConnect),
    NoTls,
    #[allow(dead_code)]
    Error(String),
}

fn count_reports(dir_path: &str) -> usize {
    let path = Path::new(dir_path);
    if !path.exists() {
        return 0;
    }
    fs::read_dir(path)
        .map(|entries| {
            entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().extension().is_some_and(|ext| ext == "md"))
                .count()
        })
        .unwrap_or(0)
}
