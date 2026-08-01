use std::str::FromStr;

fn main() {
    let mut parsed_url = url::Url::parse("postgresql://user:pass@host/db?sslmode=require&channel_binding=require").unwrap();
    let pairs: Vec<_> = parsed_url.query_pairs().into_owned().filter(|(k, _)| k != "channel_binding").collect();
    parsed_url.query_pairs_mut().clear().extend_pairs(pairs.into_iter());
    println!("{}", parsed_url.to_string());
}
