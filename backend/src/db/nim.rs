use crate::config::Settings;
use reqwest::Client;
use serde_json::{json, Value};
use std::sync::Mutex;
use std::time::{Duration, Instant};

static SHARED_CLIENT: std::sync::LazyLock<Client> = std::sync::LazyLock::new(|| {
    Client::builder()
        .connect_timeout(std::time::Duration::from_secs(10))
        .tcp_keepalive(std::time::Duration::from_secs(30))
        .build()
        .expect("Failed to build NIM reqwest Client")
});

struct NimRateLimiter {
    timestamps: Vec<Instant>,
}

impl NimRateLimiter {
    fn check(&mut self, limit: usize, window: Duration) -> Option<u32> {
        let now = Instant::now();
        self.timestamps
            .retain(|ts| now.duration_since(*ts) < window);

        if self.timestamps.len() >= limit {
            let retry_after = match self.timestamps.first() {
                Some(oldest) => (window - now.duration_since(*oldest)).as_secs().max(1) as u32,
                None => window.as_secs() as u32,
            };
            return Some(retry_after);
        }

        self.timestamps.push(now);
        None
    }
}

static NIM_RATE_LIMITER: std::sync::LazyLock<Mutex<NimRateLimiter>> =
    std::sync::LazyLock::new(|| {
        Mutex::new(NimRateLimiter {
            timestamps: Vec::new(),
        })
    });

/// Enforces the account-level NIM request cap (default 40 RPM on the free tier).
/// Returns `Some(retry_after_secs)` if the request must be deferred.
fn check_rate_limit() -> Option<u32> {
    let limit = Settings::global().nvidia_nim_rpm.max(1) as usize;
    let mut guard = NIM_RATE_LIMITER.lock().unwrap_or_else(|e| e.into_inner());
    guard.check(limit, Duration::from_secs(60))
}

#[derive(Debug, Clone)]
pub struct GeneratedQuiz {
    pub question: String,
    pub answer: String,
    pub options: Vec<String>,
}

pub async fn generate_quiz(category: &str) -> Result<GeneratedQuiz, String> {
    let settings = Settings::global();
    if settings.nvidia_nim_key.is_empty() {
        return Err("NVIDIA NIM API key is not configured".to_string());
    }

    if let Some(retry_after) = check_rate_limit() {
        return Err(format!(
            "NVIDIA NIM rate limit reached ({} rpm). Try again in {} seconds.",
            settings.nvidia_nim_rpm.max(1),
            retry_after
        ));
    }

    let base_url = settings.nvidia_nim_url.trim_end_matches('/').to_string();
    let url = format!("{}/chat/completions", base_url);

    let payload = json!({
        "model": settings.nvidia_nim_model,
        "messages": [
            {
                "role": "system",
                "content": "You are Nico Robin, archaeologist of the Straw Hat Pirates, master of the Poneglyph Quiz. Compose ONE multiple-choice trivia question about the world of One Piece — its history, islands, characters, Devil Fruits and lore — as if deciphering an ancient riddle. Reply with ONLY valid JSON in exactly this shape: {\"question\": \"<the question>\", \"options\": [\"<a>\", \"<b>\", \"<c>\", \"<d>\"], \"answer\": \"<exact text of the correct option>\"}. Provide EXACTLY 4 distinct options. The answer field must be an exact copy of the correct option string. Keep options short (1 to 6 words). Make the question elegant and scholarly, in Robin's voice — calm, curious, faintly amused."
            },
            {
                "role": "user",
                "content": format!("Category: {}\nReturn only the JSON object, nothing else.", category)
            }
        ],
        "temperature": 0.7,
        "max_tokens": 256,
        "response_format": { "type": "json_object" }
    });

    let resp = SHARED_CLIENT
        .post(&url)
        .bearer_auth(&settings.nvidia_nim_key)
        .json(&payload)
        .timeout(std::time::Duration::from_secs(settings.nvidia_nim_timeout))
        .send()
        .await
        .map_err(|e| format!("NIM request failed: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("NIM API error ({}): {}", status, body));
    }

    let body: Value = resp
        .json()
        .await
        .map_err(|e| format!("NIM invalid response: {}", e))?;

    let content = body["choices"][0]["message"]["content"]
        .as_str()
        .ok_or_else(|| "NIM response contained no message content".to_string())?;

    parse_quiz_json(content)
}

fn parse_quiz_json(content: &str) -> Result<GeneratedQuiz, String> {
    let mut json_str = content.trim().to_string();
    if json_str.starts_with("```") {
        let lines: Vec<&str> = json_str
            .lines()
            .skip(1)
            .take_while(|l| !l.trim().starts_with("```"))
            .collect();
        json_str = lines.join("\n");
    }

    let start = json_str
        .find('{')
        .ok_or_else(|| "NIM response contained no JSON object".to_string())?;
    let end = json_str
        .rfind('}')
        .ok_or_else(|| "NIM response contained no JSON object".to_string())?;

    let val: Value = serde_json::from_str(&json_str[start..=end])
        .map_err(|e| format!("Failed to parse NIM JSON: {}", e))?;

    let question = val["question"]
        .as_str()
        .ok_or_else(|| "NIM response missing question".to_string())?
        .trim()
        .to_string();
    let answer = val["answer"]
        .as_str()
        .ok_or_else(|| "NIM response missing answer".to_string())?
        .trim()
        .to_string();

    let mut options: Vec<String> = val["options"]
        .as_array()
        .ok_or_else(|| "NIM response missing options".to_string())?
        .iter()
        .filter_map(|o| o.as_str().map(|s| s.trim().to_string()))
        .filter(|s| !s.is_empty())
        .collect();

    if question.is_empty() || answer.is_empty() {
        return Err("NIM generated an empty question or answer".to_string());
    }
    if options.len() != 4 {
        return Err(format!(
            "NIM generated {} options, expected exactly 4",
            options.len()
        ));
    }

    // De-duplicate while preserving order, then trim to 4 if a duplicate crept in.
    let mut seen = std::collections::HashSet::new();
    options.retain(|o| seen.insert(o.to_lowercase()));

    if !options.contains(&answer) {
        return Err("NIM answer does not match any generated option".to_string());
    }

    Ok(GeneratedQuiz {
        question,
        answer,
        options,
    })
}
