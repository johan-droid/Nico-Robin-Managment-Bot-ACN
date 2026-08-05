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
    question_id: i32,
    answer: String,
    options: Vec<String>,
    expires_at: Instant,
    attempts: HashMap<i64, bool>,
}

pub static ACTIVE_QUIZZES: LazyLock<Arc<Mutex<HashMap<i64, ActiveQuiz>>>> =
    LazyLock::new(|| Arc::new(Mutex::new(HashMap::new())));

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
    WrongAnswer { question_id: i32 },
    CorrectAnswer { answer: String, question_id: i32 },
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
        Some((question_id, quiz)) => {
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

            match send_msg_result {
            Ok(sent) => {
                let mut guard = ACTIVE_QUIZZES.lock().await;
                guard.insert(
                    chat_id,
                    ActiveQuiz {
                        message_id: sent.message_id,
                        question_id,
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
            Err(e) => {
                tracing::error!(error = %e, chat_id = %chat_id, "Failed to send quiz message");
                // Roll back the cooldowns so the failed attempt doesn't lock
                // the user and chat out of the next quiz.
                let mut user_guard = USER_QUIZ_COOLDOWN.lock().await;
                user_guard.remove(&user_id);
                let mut chat_guard = CHAT_QUIZ_COOLDOWN.lock().await;
                chat_guard.remove(&chat_id);
                let _ = bot
                    .send_message(
                        chat_id,
                        "Fufufu... the Poneglyph refused to appear. Please try again.",
                    )
                    .await;
            }
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
        let question_id = quiz.question_id;
        guard.remove(&chat_id);
        QuizOutcome::CorrectAnswer {
            answer: ans,
            question_id,
        }
    } else {
        quiz.attempts.insert(user_id, false);
        QuizOutcome::WrongAnswer {
            question_id: quiz.question_id,
        }
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
            let question_id = quiz.question_id;
            guard.remove(&chat_id);
            QuizOutcome::CorrectAnswer {
                answer: ans,
                question_id,
            }
        }
        Some(_) => {
            quiz.attempts.insert(user_id, false);
            QuizOutcome::WrongAnswer {
                question_id: quiz.question_id,
            }
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
        QuizOutcome::CorrectAnswer {
            answer,
            question_id,
        } => {
            let credited = match crate::db::games::add_bounty(client, user_id, 10).await {
                Ok(_) => true,
                Err(e) => {
                    tracing::error!(error = %e, user_id = %user_id, "Failed to credit quiz bounty");
                    false
                }
            };
            let _ = crate::db::game_stats::record_game_play(client, user_id, "quiz", true).await;
            let _ = crate::db::quiz_tracker::record_quiz_attempt(
                client, chat_id, question_id, user_id, true,
            )
            .await;
            let credit_line = if credited {
                "➕ <b>+10 Bounty</b>\n\n"
            } else {
                ""
            };
            let reply = format!(
                "Fufufu... beautifully deciphered, dear pirate. The truth has been revealed.\n\n{}The answer was: <b>{}</b>",
                credit_line, answer
            );
            let _ = bot
                .send_message(chat_id, reply)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        QuizOutcome::WrongAnswer { question_id } => {
            let _ = crate::db::games::add_bounty(client, user_id, -5).await;
            let _ = crate::db::game_stats::record_game_play(client, user_id, "quiz", false).await;
            let _ = crate::db::quiz_tracker::record_quiz_attempt(
                client, chat_id, question_id, user_id, false,
            )
            .await;
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

/// Fetches the next quiz question. Returns the question id alongside the
/// question data so attempts can be persisted against the exact question.
/// Tracks recent ids per chat in `quiz_history` (survives restarts).
async fn next_quiz(client: &Client, chat_id: i64) -> Option<(i32, QuizData)> {
    let excluded = recent_question_ids(client, chat_id).await;

    if !Settings::global().nvidia_nim_key.is_empty() {
        match crate::db::nim::generate_quiz("one_piece").await {
            Ok(generated) => {
                if let Ok(id) = crate::db::games::add_quiz_question(
                    client,
                    &generated.question,
                    &generated.answer,
                    &generated.options,
                )
                .await
                {
                    return Some((
                        id,
                        QuizData {
                            question: generated.question,
                            answer: generated.answer,
                            options: generated.options,
                        },
                    ));
                }
            }
            Err(e) => {
                tracing::warn!(
                    "NIM quiz generation failed, falling back to stored questions: {}",
                    e
                );
            }
        }
    }

    match crate::db::quiz_tracker::get_random_quiz_smart(client, &excluded).await {
        Ok(Some((id, question, answer, options))) => Some((
            id,
            QuizData {
                question,
                answer,
                options,
            },
        )),
        // All stored questions were recently used; fall back to any question.
        Ok(None) => match crate::db::games::get_random_quiz(client).await {
            Ok(Some(q)) => Some((
                q.id,
                QuizData {
                    question: q.question,
                    answer: q.answer,
                    options: q.options,
                },
            )),
            _ => None,
        },
        Err(e) => {
            tracing::error!("Error fetching quiz: {}", e);
            None
        }
    }
}

/// Question ids recently asked in this chat, most recent first.
async fn recent_question_ids(client: &Client, chat_id: i64) -> Vec<i32> {
    match crate::db::quiz_tracker::get_recent_question_ids_db(client, chat_id, 30i64).await {
        Ok(ids) => ids,
        Err(e) => {
            tracing::warn!("Failed to load recent quiz ids for chat {}: {}", chat_id, e);
            vec![]
        }
    }
}

/// `/quizstats` — the user's personal quiz performance.
pub async fn handle_quizstats(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    let user_id = msg.from().map(|u| u.id).unwrap_or(0) as i64;
    if user_id == 0 {
        return Ok(());
    }

    match crate::db::quiz_tracker::get_user_quiz_stats(client, user_id).await {
        Ok(Some(s)) => {
            let name = msg
                .from()
                .map(|u| u.first_name.clone())
                .unwrap_or_else(|| "Pirate".to_string());
            let text = format!(
                "📚 <b>Poneglyph Record</b>\n\n\
                 <b>{}</b>\n\n\
                 ✅ Correct: <b>{}</b>\n\
                 ❌ Wrong: <b>{}</b>\n\
                 🎯 Accuracy: <b>{:.1}%</b>\n\
                 🎮 Total attempts: <b>{}</b>",
                crate::utils::escape_html(&name),
                s.correct_answers,
                s.wrong_answers,
                s.accuracy,
                s.total_attempts
            );
            let _ = bot
                .send_message(chat_id, text)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
        Ok(None) => {
            let text =
                "Fufufu... You have not deciphered a single Poneglyph yet, dear pirate. Try /quiz!";
            let _ = bot.send_message(chat_id, text).await;
        }
        Err(e) => {
            tracing::error!("Failed to load quiz stats for user {}: {}", user_id, e);
            let _ = bot
                .send_message(chat_id, "Fufufu... the archives are out of reach. Try again later.")
                .await;
        }
    }
    Ok(())
}

/// `/qleaderboard` — top quiz deciphers across all chats.
pub async fn handle_qleaderboard(
    bot: Bot,
    msg: Message,
    client: &Client,
) -> Result<(), String> {
    let chat_id = msg.chat.id;

    let entries = match crate::db::quiz_tracker::get_quiz_leaderboard(client, 10).await {
        Ok(e) => e,
        Err(e) => {
            tracing::error!("Failed to load quiz leaderboard: {}", e);
            let _ = bot
                .send_message(chat_id, "Fufufu... the archives are out of reach. Try again later.")
                .await;
            return Ok(());
        }
    };

    if entries.is_empty() {
        let _ = bot
            .send_message(
                chat_id,
                "Fufufu... No pirate has deciphered a Poneglyph yet. Be the first with /quiz!",
            )
            .await;
        return Ok(());
    }

    let user_ids: Vec<i64> = entries.iter().map(|e| e.1).collect();
    let names = crate::db::leaderboard::resolve_user_names(client, &user_ids).await;

    let mut lines = vec!["👑 <b>Top Poneglyph Deciphers</b>".to_string()];
    for (rank, user_id, correct, total, accuracy) in entries {
        let name = names
            .get(&user_id)
            .cloned()
            .unwrap_or_else(|| "Unknown Pirate".to_string());
        let medal = match rank {
            1 => "🥇",
            2 => "🥈",
            3 => "🥉",
            _ => "🎴",
        };
        lines.push(format!(
            "{} <b>{}</b> — {} correct / {} ({:.1}%)",
            medal,
            crate::utils::escape_html(&name),
            correct,
            total,
            accuracy
        ));
    }

    let _ = bot
        .send_message(chat_id, lines.join("\n"))
        .parse_mode(crate::telegram::ParseMode::Html)
        .await;
    Ok(())
}

/// `/quiz:admin` — moderator-only quiz pool management.
///   /quiz:admin stats        — pool totals and usage
///   /quiz:admin reset <id>   — clear usage tracking for a question
///   /quiz:admin remove <id>  — delete a question from the pool
pub async fn handle_quiz_admin(bot: Bot, msg: Message, client: &Client) -> Result<(), String> {
    let chat_id = msg.chat.id;
    let text = msg.text().unwrap_or("");
    let parts: Vec<&str> = text.split_whitespace().collect();
    let sub = parts
        .get(1)
        .map(|s| s.to_ascii_lowercase())
        .unwrap_or_else(|| "stats".to_string());

    match sub.as_str() {
        "stats" => match crate::db::quiz_tracker::quiz_pool_stats(client).await {
            Ok((total, used)) => {
                let text = format!(
                    "📊 <b>Quiz Pool</b>\n\n\
                     📚 Total questions: <b>{}</b>\n\
                     🔁 Already used: <b>{}</b>\n\
                     ✨ Fresh questions: <b>{}</b>",
                    total,
                    used,
                    total - used
                );
                let _ = bot
                    .send_message(chat_id, text)
                    .parse_mode(crate::telegram::ParseMode::Html)
                    .await;
            }
            Err(e) => {
                tracing::error!("Failed to load quiz pool stats: {}", e);
                let _ = bot
                    .send_message(chat_id, "Fufufu... the archives are out of reach.")
                    .await;
            }
        },
        "reset" => {
            let id: i32 = match parts.get(2).and_then(|p| p.parse().ok()) {
                Some(id) => id,
                None => {
                    let _ = bot
                        .send_message(
                            chat_id,
                            "Usage: <b>/quiz:admin reset &lt;question_id&gt;</b>".to_string(),
                        )
                        .parse_mode(crate::telegram::ParseMode::Html)
                        .await;
                    return Ok(());
                }
            };
            match crate::db::quiz_tracker::reset_question_usage(client, id).await {
                Ok(true) => {
                    let _ = bot
                        .send_message(
                            chat_id,
                            format!(
                                "🗑️ Usage reset for question <b>{}</b>. It can appear again.",
                                id
                            ),
                        )
                        .parse_mode(crate::telegram::ParseMode::Html)
                        .await;
                }
                Ok(false) => {
                    let _ = bot
                        .send_message(chat_id, format!("No question with id {} found.", id))
                        .await;
                }
                Err(e) => {
                    tracing::error!("Failed to reset usage for question {}: {}", id, e);
                    let _ = bot
                        .send_message(chat_id, "Fufufu... the archives are out of reach.")
                        .await;
                }
            }
        }
        "remove" => {
            let id: i32 = match parts.get(2).and_then(|p| p.parse().ok()) {
                Some(id) => id,
                None => {
                    let _ = bot
                        .send_message(
                            chat_id,
                            "Usage: <b>/quiz:admin remove &lt;question_id&gt;</b>".to_string(),
                        )
                        .parse_mode(crate::telegram::ParseMode::Html)
                        .await;
                    return Ok(());
                }
            };
            match crate::db::quiz_tracker::remove_question(client, id).await {
                Ok(true) => {
                    let _ = bot
                        .send_message(
                            chat_id,
                            format!("🗑️ Removed question <b>{}</b> from the pool.", id),
                        )
                        .parse_mode(crate::telegram::ParseMode::Html)
                        .await;
                }
                Ok(false) => {
                    let _ = bot
                        .send_message(chat_id, format!("No question with id {} found.", id))
                        .await;
                }
                Err(e) => {
                    tracing::error!("Failed to remove question {}: {}", id, e);
                    let _ = bot
                        .send_message(chat_id, "Fufufu... the archives are out of reach.")
                        .await;
                }
            }
        }
        _ => {
            let help = "🔧 <b>Quiz Admin</b>\n\n\
                        /quiz:admin stats — pool totals\n\
                        /quiz:admin reset &lt;id&gt; — reset usage tracking\n\
                        /quiz:admin remove &lt;id&gt; — delete a question";
            let _ = bot
                .send_message(chat_id, help)
                .parse_mode(crate::telegram::ParseMode::Html)
                .await;
        }
    }
    Ok(())
}
