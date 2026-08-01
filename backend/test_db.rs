use std::str::FromStr;
fn main() {
    let mut cfg = tokio_postgres::Config::from_str("postgresql://user:pass@host1.com/db").unwrap();
    cfg.host("1.2.3.4");
    println!("{:?}", cfg.get_hosts());
}
