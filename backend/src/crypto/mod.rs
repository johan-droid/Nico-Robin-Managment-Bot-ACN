use aes_gcm::{
    aead::{Aead, AeadCore, KeyInit, OsRng},
    Aes256Gcm, Nonce,
};
use base64::{
    engine::general_purpose::STANDARD as BASE64,
    Engine,
};
use hmac::{Hmac, Mac};
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

type HmacSha256 = Hmac<Sha256>;

const NONCE_SIZE: usize = 12;

static CRYPTO: OnceLock<Crypto> = OnceLock::new();

pub struct Crypto {
    cipher: Aes256Gcm,
    hmac_key: Vec<u8>,
}

impl Crypto {
    pub fn from_hex_key(hex_key: &str) -> Self {
        let raw = hex::decode(hex_key).expect("ENCRYPTION_KEY must be a valid hex string (64+ hex chars for 32+ bytes)");
        let key = Sha256::digest(&raw);
        let cipher = Aes256Gcm::new_from_slice(&key).expect("Failed to create AES-256-GCM cipher");
        let hmac_key = key.to_vec();
        Self { cipher, hmac_key }
    }

    pub fn encrypt_text(&self, plaintext: &str) -> String {
        let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
        let ciphertext = self
            .cipher
            .encrypt(&nonce, plaintext.as_bytes())
            .expect("Encryption failed");
        let mut result = nonce.to_vec();
        result.extend(ciphertext);
        BASE64.encode(&result)
    }

    pub fn decrypt_text(&self, encrypted: &str) -> Option<String> {
        let data = BASE64.decode(encrypted).ok()?;
        if data.len() < NONCE_SIZE {
            return None;
        }
        let (nonce_bytes, ciphertext) = data.split_at(NONCE_SIZE);
        let nonce = Nonce::from_slice(nonce_bytes);
        let plaintext = self.cipher.decrypt(nonce, ciphertext).ok()?;
        String::from_utf8(plaintext).ok()
    }

    pub fn hash_id(&self, id: i64) -> String {
        let mut mac = <HmacSha256 as KeyInit>::new_from_slice(&self.hmac_key)
            .expect("HMAC key creation failed");
        mac.update(&id.to_le_bytes());
        let result = mac.finalize();
        BASE64.encode(result.into_bytes())
    }

    pub fn encrypt_id(&self, id: i64) -> String {
        self.encrypt_text(&id.to_string())
    }

    pub fn decrypt_id(&self, encrypted: &str) -> Option<i64> {
        self.decrypt_text(encrypted)?.parse().ok()
    }

    pub fn hash_text(&self, text: &str) -> String {
        let mut mac = <HmacSha256 as KeyInit>::new_from_slice(&self.hmac_key)
            .expect("HMAC key creation failed");
        mac.update(text.as_bytes());
        let result = mac.finalize();
        BASE64.encode(result.into_bytes())
    }
}

pub fn init(hex_key: &str) {
    let crypto = Crypto::from_hex_key(hex_key);
    CRYPTO.set(crypto).ok().expect("Crypto already initialized");
}

pub fn global() -> &'static Crypto {
    CRYPTO.get().expect("Crypto not initialized. Call crypto::init() at startup")
}

/// Return the Crypto instance if initialized, or `None` if no key was configured.
pub fn try_crypto() -> Option<&'static Crypto> {
    CRYPTO.get()
}

/// Encrypt text if crypto is initialized, otherwise return the original plaintext.
pub fn try_encrypt(plaintext: &str) -> String {
    match try_crypto() {
        Some(c) => c.encrypt_text(plaintext),
        None => plaintext.to_string(),
    }
}

/// Decrypt text if crypto is initialized; if decryption fails (e.g. old plaintext),
/// return the original value unchanged so data can be re-encrypted on next write.
pub fn try_decrypt(value: &str) -> String {
    match try_crypto() {
        Some(c) => c.decrypt_text(value).unwrap_or_else(|| value.to_string()),
        None => value.to_string(),
    }
}
