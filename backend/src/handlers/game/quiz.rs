use crate::config::Settings;
use crate::telegram::api::Bot;
use crate::telegram::update::{CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message};
use std::collections::HashMap;
use std::sync::Arc;
use std::sync::LazyLock;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;
use tokio_postgres::Client;

pub struct ActiveQuiz {
    pub message_id: u64,
    answer: String,
    options: Vec<String>,
    expires_at: Instant,
    attempts: HashMap<i64, bool>,
}

pub static ACTIVE_QUIZZES: LazyLock<Arc<Mutex<HashMap<i64, ActiveQuiz>>>> =
    LazyLock::new(|| Arc::new(Mutex::new(HashMap::new())));

static RECENT_QUIZ_IDS: LazyLock<Arc<Mutex<HashMap<i64, Vec<i32>>>>> =
    LazyLock::new(|| Arc::new(Mutex::new(HashMap::new())));

const RECENT_LIMIT: usize = 50;

static USER_QUIZ_COOLDOWN: LazyLock<Arc<Mutex<HashMap<i64, Instant>>>> =
    LazyLock::new(|| Arc::new(Mutex::new(HashMap::new())));

static CHAT_QUIZ_COOLDOWN: LazyLock<Arc<Mutex<HashMap<i64, Instant>>>> =
    LazyLock::new(|| Arc::new(Mutex::new(HashMap::new())));

const USER_COOLDOWN_SECS: u64 = 3600; // 1 hour per user
const CHAT_COOLDOWN_SECS: u64 = 300; // 5 mins per chat

#[derive(Debug, Clone, PartialEq)]
pub enum QuizOutcome {
    NoActiveQuiz,
    AlreadyAnswered,
    WrongAnswer,
    CorrectAnswer { answer: String },
}

struct QuizData {
    question: String,
    answer: String,
    options: Vec<String>,
}

pub async fn handle_quiz(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    let user_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    if user_id == 0 {
        return Ok(());
    }

    {
        let guard = ACTIVE_QUIZZES.lock().await;
        if guard.contains_key(&chat_id) {
            let _ = bot.send_message(chat_id, "Fufufu... There is already an active Poneglyph in this chat. Decipher it first!").await;
            return Ok(());
        }
    }

    {
        let mut user_guard = USER_QUIZ_COOLDOWN.lock().await;
        if let Some(&last) = user_guard.get(&user_id) {
            if last.elapsed() < Duration::from_secs(USER_COOLDOWN_SECS) {
                let remaining = USER_COOLDOWN_SECS - last.elapsed().as_secs();
                let _ = bot
                    .send_message(
                        chat_id,
                        format!(
                            "Fufufu... You must wait {} minutes before reading another Poneglyph.",
                            remaining / 60 + 1
                        ),
                    )
                    .await;
                return Ok(());
            }
        }

        let mut chat_guard = CHAT_QUIZ_COOLDOWN.lock().await;
        if let Some(&last) = chat_guard.get(&chat_id) {
            if last.elapsed() < Duration::from_secs(CHAT_COOLDOWN_SECS) {
                let remaining = CHAT_COOLDOWN_SECS - last.elapsed().as_secs();
                let _ = bot
                    .send_message(
                        chat_id,
                        format!(
                            "The ruins are quiet. A new Poneglyph may appear here in {} minutes.",
                            remaining / 60 + 1
                        ),
                    )
                    .await;
                return Ok(());
            }
        }

        user_guard.insert(user_id, Instant::now());
        chat_guard.insert(chat_id, Instant::now());
    }
    let quiz = next_quiz(client, chat_id).await;

    match quiz {
        Some(quiz) => {
            let timeout_secs = Settings::global().quiz_timeout_secs.clamp(10, 20);

            let text = if quiz.options.is_empty() {
                format!(
                    "🧠 <b>Poneglyph Quiz</b>\n\n\
                     <b>Question:</b>\n{}\n\n\
                     <b>Rules:</b>\n\
                     • One attempt per pirate.\n\
                     • First correct answer: <b>+10 Bounty</b>\n\
                     • Wrong answer: <b>-5 Bounty</b>\n\n\
                     ⏰ You have <b>{} seconds</b>. Reply to this message with your answer!",
                    quiz.question, timeout_secs
                )
            } else {
                format!(
                    "🧠 <b>Poneglyph Quiz</b>\n\n\
                     <b>Question:</b>\n{}\n\n\
                     <b>Options:</b>\n{}\n\n\
                     <b>Rules:</b>\n\
                     • One attempt per pirate.\n\
                     • First correct answer: <b>+10 Bounty</b>\n\
                     • Wrong answer: <b>-5 Bounty</b>\n\n\
                     ⏰ You have <b>{} seconds</b>. Tap an option below to answer!",
                    quiz.question,
                    numbered_options(&quiz.options),
                    timeout_secs
                )
            };

            let mut builder = bot
                .send_message(msg.chat.id, text)
                .parse_mode(crate::telegram::ParseMode::Html);
            if !quiz.options.is_empty() {
                builder = builder.reply_markup(quiz_keyboard(&quiz.options));
            }
            let send_msg_result = builder.await;

            if let Ok(sent) = send_msg_result {
                let mut guard = ACTIVE_QUIZZES.lock().await;
                guard.insert(
                    chat_id,
                    ActiveQuiz {
                        message_id: sent.message_id,
                        answer: quiz.answer,
                        options: quiz.options,
                        expires_at: Instant::now() + Duration::from_secs(timeout_secs),
                        attempts: HashMap::new(),
                    },
                );
                drop(guard);

                let bot_clone = bot.clone();
                tokio::spawn(async move {
                    tokio::time::sleep(Duration::from_secs(timeout_secs)).await;
                    let revealed = {
                        let mut guard = ACTIVE_QUIZZES.lock().await;
                        if let Some(quiz) = guard.get(&chat_id) {
                            if quiz.expires_at <= Instant::now() {
                                let ans = quiz.answer.clone();
                                guard.remove(&chat_id);
                                Some(ans)
                            } else {
                                None
                            }
                        } else {
                            None
                        }
                    };
                    if let Some(ans) = revealed {
                        let _ = bot_clone
                            .send_message(
                                chat_id,
                                format!(
                                    "⏳ Time's up, dear pirates... This Poneglyph remains unread.\n\nThe answer was: <b>{}</b>",
                                    ans
                                ),
                            )
                            .parse_mode(crate::telegram::ParseMode::Html)
                            .await;
                    }
                });
            }
        }
        None => {
            {
                let mut user_guard = USER_QUIZ_COOLDOWN.lock().await;
                user_guard.remove(&user_id);
                let mut chat_guard = CHAT_QUIZ_COOLDOWN.lock().await;
                chat_guard.remove(&chat_id);
            }
            let text = "Fufufu... The archive is empty for now, dear pirate. Do try again later.";
            let _ = bot.send_message(msg.chat.id, text).await;
        }
    }
    Ok(())
}

/// Handles a tap on one of the multiple-choice option buttons.
/// Callback data format: `qz<index>` (e.g. `qz0`..`qz3`).
pub async fn handle_quiz_callback(
    bot: Bot,
    cq: CallbackQuery,
    client: &Client,
) -> Result<(), String> {
    let _ = bot.answer_callback_query(&cq.id).await;

    let (chat_id, message_id) = match cq.message.as_ref() {
        Some(m) => (m.chat.id, m.id()),
        None => return Ok(()),
    };
    let user_id = cq.from.id as i64;

    let Some(data) = cq.data.as_deref() else {
        return Ok(());
    };
    if !data.starts_with("qz") {
        return Ok(());
    }
    let Ok(choice) = data[2..].parse::<usize>() else {
        return Ok(());
    };

    let outcome = evaluate_choice(chat_id, user_id, choice, message_id).await;
    apply_quiz_result(&bot, client, chat_id, user_id, outcome).await;
    Ok(())
}

/// Evaluates a reply against the active quiz for this chat, enforcing the
/// strict timer and the one-attempt-per-pirate anti-cheat rule.
pub async fn evaluate_answer(
    chat_id: i64,
    user_id: i64,
    answer: &str,
    reply_to_msg_id: Option<u64>,
) -> QuizOutcome {
    let mut guard = ACTIVE_QUIZZES.lock().await;
    let quiz = match guard.get_mut(&chat_id) {
        Some(q) => q,
        None => return QuizOutcome::NoActiveQuiz,
    };

    if reply_to_msg_id != Some(quiz.message_id) || Instant::now() >= quiz.expires_at {
        return QuizOutcome::NoActiveQuiz;
    }

    if quiz.attempts.contains_key(&user_id) {
        return QuizOutcome::AlreadyAnswered;
    }

    if normalize(answer) == normalize(&quiz.answer) {
        let ans = quiz.answer.clone();
        guard.remove(&chat_id);
        QuizOutcome::CorrectAnswer { answer: ans }
    } else {
        quiz.attempts.insert(user_id, false);
        QuizOutcome::WrongAnswer
    }
}

/// Evaluates a tapped option button.
async fn evaluate_choice(
    chat_id: i64,
    user_id: i64,
    choice: usize,
    reply_to_msg_id: u64,
) -> QuizOutcome {
    let mut guard = ACTIVE_QUIZZES.lock().await;
    let quiz = match guard.get_mut(&chat_id) {
        Some(q) => q,
        None => return QuizOutcome::NoActiveQuiz,
    };

    if reply_to_msg_id != quiz.message_id || Instant::now() >= quiz.expires_at {
        return QuizOutcome::NoActiveQuiz;
    }

    if quiz.attempts.contains_key(&user_id) {
        return QuizOutcome::AlreadyAnswered;
    }

    match quiz.options.get(choice) {
        Some(chosen) if normalize(chosen) == normalize(&quiz.answer) => {
            let ans = quiz.answer.clone();
            guard.remove(&chat_id);
            QuizOutcome::CorrectAnswer { answer: ans }
        }
        Some(_) => {
            quiz.attempts.insert(user_id, false);
            QuizOutcome::WrongAnswer
        }
        None => QuizOutcome::NoActiveQuiz,
    }
}

/// Sends the reward/penalty reply for a quiz outcome and applies bounty changes.
pub async fn apply_quiz_result(
    bot: &Bot,
    client: &Client,
    chat_id: i64,
    user_id: i64,
    outcome: QuizOutcome,
) {
    match outcome {
        QuizOutcome::CorrectAnswer { answer } => {
            let _ = crate::db::games::add_bounty(client, user_id, 10).await;
            let reply = format!(
                "Fufufu... beautifully deciphered, dear pirate. The truth has been revealed.\n\n➕ <b>+10 Bounty</b>\n\nThe answer was: <b>{}</b>",
                answer
            );
            let _ = bot
                .send_message(chat_id, reply)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        QuizOutcome::WrongAnswer => {
            let _ = crate::db::games::add_bounty(client, user_id, -5).await;
            let reply = "Hmm... not quite, dear. The truth eludes you this time.\n\n➖ <b>-5 Bounty</b>\n\nThis Poneglyph will not grant you a second reading."
                .to_string();
            let _ = bot.send_message(chat_id, reply).await;
        }
        QuizOutcome::AlreadyAnswered => {
            let reply =
                "You have already attempted this reading, dear pirate. One attempt per Poneglyph."
                    .to_string();
            let _ = bot.send_message(chat_id, reply).await;
        }
        _ => {}
    }
}

fn numbered_options(options: &[String]) -> String {
    options
        .iter()
        .enumerate()
        .map(|(i, opt)| format!("{} {}", num_emoji(i + 1), opt))
        .collect::<Vec<_>>()
        .join("\n")
}

fn num_emoji(n: usize) -> &'static str {
    match n {
        1 => "1️⃣",
        2 => "2️⃣",
        3 => "3️⃣",
        4 => "4️⃣",
        _ => "•",
    }
}

fn quiz_keyboard(options: &[String]) -> InlineKeyboardMarkup {
    let inline_keyboard = options
        .iter()
        .enumerate()
        .map(|(i, opt)| {
            vec![InlineKeyboardButton {
                text: format!("{} {}", num_emoji(i + 1), opt),
                callback_data: Some(format!("qz{}", i)),
                url: None,
            }]
        })
        .collect();
    InlineKeyboardMarkup { inline_keyboard }
}

fn normalize(s: &str) -> String {
    s.split_whitespace()
        .map(|w| w.trim_matches(|c: char| !c.is_alphanumeric()))
        .filter(|w| !w.is_empty())
        .collect::<Vec<_>>()
        .join(" ")
        .to_ascii_lowercase()
}

async fn next_quiz(client: &Client, chat_id: i64) -> Option<QuizData> {
    let excluded = recent_ids(chat_id).await;

    if !Settings::global().nvidia_nim_key.is_empty() {
        match crate::db::nim::generate_quiz("one_piece").await {
            Ok(generated) => {
                let id = crate::db::games::add_quiz_question(
                    client,
                    &generated.question,
                    &generated.answer,
                    &generated.options,
                )
                .await
                .ok();
                if let Some(id) = id {
                    record_recent_id(chat_id, id).await;
                }
                return Some(QuizData {
                    question: generated.question,
                    answer: generated.answer,
                    options: generated.options,
                });
            }
            Err(e) => {
                tracing::warn!(
                    "NIM quiz generation failed, falling back to stored questions: {}",
                    e
                );
            }
        }
    }

    match crate::db::games::get_random_quiz_excluding(client, &excluded).await {
        Ok(Some(q)) => {
            record_recent_id(chat_id, q.id).await;
            Some(QuizData {
                question: q.question,
                answer: q.answer,
                options: q.options,
            })
        }
        Ok(None) => match crate::db::games::get_random_quiz_excluding(client, &[]).await {
            Ok(Some(q)) => {
                record_recent_id(chat_id, q.id).await;
                Some(QuizData {
                    question: q.question,
                    answer: q.answer,
                    options: q.options,
                })
            }
            _ => None,
        },
        Err(e) => {
            tracing::error!("Error fetching quiz: {}", e);
            None
        }
    }
}

async fn record_recent_id(chat_id: i64, id: i32) {
    let mut guard = RECENT_QUIZ_IDS.lock().await;
    let list = guard.entry(chat_id).or_default();
    if !list.contains(&id) {
        list.push(id);
    }
    while list.len() > RECENT_LIMIT {
        list.remove(0);
    }
}

async fn recent_ids(chat_id: i64) -> Vec<i32> {
    let guard = RECENT_QUIZ_IDS.lock().await;
    guard.get(&chat_id).cloned().unwrap_or_default()
}
