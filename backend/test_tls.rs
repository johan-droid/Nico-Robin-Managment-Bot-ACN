use std::error::Error;
use tokio_postgres::tls::MakeTlsConnect;

struct CustomTlsConnect {
    inner: tokio_postgres_rustls::MakeRustlsConnect,
    domain: String,
}

impl<S> MakeTlsConnect<S> for CustomTlsConnect
where
    tokio_postgres_rustls::MakeRustlsConnect: MakeTlsConnect<S>,
{
    type Stream = <tokio_postgres_rustls::MakeRustlsConnect as MakeTlsConnect<S>>::Stream;
    type TlsConnect = <tokio_postgres_rustls::MakeRustlsConnect as MakeTlsConnect<S>>::TlsConnect;
    type Error = <tokio_postgres_rustls::MakeRustlsConnect as MakeTlsConnect<S>>::Error;

    fn make_tls_connect(&mut self, _domain: &str) -> Result<Self::TlsConnect, Self::Error> {
        self.inner.make_tls_connect(&self.domain)
    }
}
fn main() {}
