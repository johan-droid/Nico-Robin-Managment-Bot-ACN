use crate::db::message_history::HistoryMessage;
use crate::telegram::api::Bot;
use crate::telegram::update::Message;
use ab_glyph::{Font, FontRef, PxScale, ScaleFont, point};
use image::{ImageEncoder, Rgba, RgbaImage};
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;
use std::sync::atomic::{AtomicU64, Ordering};

const FONT_DATA: &[u8] = include_bytes!("../../assets/DejaVuSans.ttf");

// ── Per-chat message history (for quoting) ─────────────────────────────

const HISTORY_MAX_PER_CHAT: usize = 500;
const MAX_QUOTE_MESSAGES: usize = 10;

/// In-memory cache of the last `HISTORY_MAX_PER_CHAT` text messages per chat.
/// The authoritative store is the `message_history` table (survives restarts);
/// this cache just avoids a DB round-trip on every `/q`.
static MESSAGE_HISTORY: std::sync::LazyLock<Mutex<HashMap<i64, VecDeque<HistoryMessage>>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));

static CHAT_PRUNE_TICKS: std::sync::LazyLock<Mutex<HashMap<i64, u64>>> =
    std::sync::LazyLock::new(|| Mutex::new(HashMap::new()));
const PRUNE_EVERY: u64 = 64;

/// Stores every text message so `/q` can look up the replied message and the
/// ones above it. Commands and empty messages are skipped. Writes through to
/// the persistent `message_history` table so quotes survive bot restarts.
pub async fn record_message(client: &tokio_postgres::Client, msg: &Message) {
    let (Some(from), Some(text)) = (msg.from(), msg.text()) else {
        return;
    };
    if text.trim().is_empty() || text.starts_with('/') {
        return;
    }
    let entry = HistoryMessage {
        message_id: msg.id(),
        user_id: from.id,
        user_name: from
            .username
            .as_deref()
            .map(|u| format!("@{}", u))
            .unwrap_or_else(|| from.first_name.clone()),
        text: text.to_string(),
        date: msg.date,
    };

    let chat_id = msg.chat.id;
    let mut count = 0u64;
    if let Ok(mut history) = MESSAGE_HISTORY.lock() {
        let buf = history.entry(chat_id).or_default();
        if let Some(last) = buf.back() {
            if last.message_id == entry.message_id {
                return;
            }
        }
        buf.push_back(entry.clone());
        while buf.len() > HISTORY_MAX_PER_CHAT {
            buf.pop_front();
        }
    }

    if let Ok(mut ticks) = CHAT_PRUNE_TICKS.lock() {
        let c = ticks.entry(chat_id).or_insert(0);
        *c = c.wrapping_add(1);
        count = *c;
    }

    let _ = crate::db::message_history::record_message(
        client,
        chat_id,
        entry.message_id,
        entry.user_id,
        &entry.user_name,
        &entry.text,
        entry.date,
    )
    .await;

    if count % PRUNE_EVERY == 0 {
        let _ = crate::db::message_history::prune_old(client, chat_id, HISTORY_MAX_PER_CHAT as i64).await;
    }
}

/// Returns history for a chat. Prefers the in-memory cache; on a cache miss
/// (e.g. right after a restart) it hydrates the cache from the database.
async fn get_history(client: &tokio_postgres::Client, chat_id: i64) -> Vec<HistoryMessage> {
    if let Some(history) = MESSAGE_HISTORY.lock().ok().and_then(|h| h.get(&chat_id).cloned()) {
        let history: Vec<HistoryMessage> = history.into_iter().collect();
        if !history.is_empty() {
            return history;
        }
    }

    match crate::db::message_history::get_recent(client, chat_id, HISTORY_MAX_PER_CHAT).await {
        Ok(messages) => {
            if let Ok(mut h) = MESSAGE_HISTORY.lock() {
                h.insert(chat_id, messages.iter().cloned().collect());
            }
            messages
        }
        Err(_) => Vec::new(),
    }
}

fn parse_quote_count(text: &str) -> usize {
    let t = text.trim();
    let t = t.strip_prefix('/').unwrap_or(t);
    let t = t.strip_prefix('q').unwrap_or(t);
    let t = t.split('@').next().unwrap_or(t).trim();
    if t.is_empty() {
        return 1;
    }
    t.parse::<usize>().unwrap_or(1).clamp(1, MAX_QUOTE_MESSAGES)
}

pub async fn handle_quote(bot: Bot, msg: Message, client: &tokio_postgres::Client) -> Result<(), String> {
    let n = parse_quote_count(msg.text().unwrap_or(""));

    let replied = match msg.reply_to_message() {
        Some(m) => m.clone(),
        None => {
            bot.send_message(
                msg.chat.id,
                "Reply to a message to quote it.\n\n\
                 /q        —  quote the replied message\n\
                 /q &lt;n&gt;  —  /q2, /q3 … quote n messages above the replied one",
            )
            .await?;
            return Ok(());
        }
    };

    let history = get_history(client, msg.chat.id).await;
    let idx = match history.iter().position(|m| m.message_id == replied.id()) {
        Some(i) => i,
        None => {
            bot.send_message(
                msg.chat.id,
                "That message is too old to quote (only the latest 500 messages are kept).\n\
                 Try quoting a more recent message.",
            )
            .await?;
            return Ok(());
        }
    };

    let start = idx.saturating_sub(n - 1);
    let selected: Vec<HistoryMessage> = history[start..=idx].to_vec();

    let selected_cloned = selected.clone();
    let webp_res = tokio::task::spawn_blocking(move || render_quote_sticker(&selected_cloned)).await;
    let webp = match webp_res {
        Ok(Ok(bytes)) => bytes,
        Ok(Err(e)) => {
            bot.send_message(msg.chat.id, format!("Could not render quote sticker: {}", e))
                .await?;
            return Ok(());
        }
        Err(e) => {
            bot.send_message(msg.chat.id, format!("Image render task failed: {}", e))
                .await?;
            return Ok(());
        }
    };

    let _ = bot.send_sticker(msg.chat.id, "quote.webp", webp).await;
    Ok(())
}

// ── Quote image rendering ──────────────────────────────────────────────

const WIDTH: u32 = 720;
const PAD: u32 = 28;
const BUBBLE_PAD_X: u32 = 20;
const BUBBLE_PAD_Y: u32 = 16;
const GAP: u32 = 16;
const RADIUS: u32 = 16;
const ACCENT_W: u32 = 6;
const NAME_SIZE: f32 = 30.0;
const TEXT_SIZE: f32 = 29.0;
const NAME_TO_TEXT_GAP: f32 = 8.0;
const MAX_TEXT_CHARS: usize = 600;

const BG: Rgba<u8> = Rgba([24, 26, 34, 255]);
const BUBBLE: Rgba<u8> = Rgba([36, 39, 52, 255]);
const TEXT_WHITE: Rgba<u8> = Rgba([233, 235, 244, 255]);

const PALETTE: [Rgba<u8>; 10] = [
    Rgba([255, 122, 92, 255]),
    Rgba([99, 179, 255, 255]),
    Rgba([130, 214, 151, 255]),
    Rgba([255, 203, 92, 255]),
    Rgba([196, 141, 255, 255]),
    Rgba([255, 143, 175, 255]),
    Rgba([92, 214, 204, 255]),
    Rgba([255, 168, 92, 255]),
    Rgba([158, 170, 255, 255]),
    Rgba([173, 223, 255, 255]),
];

fn user_color(user_id: u64) -> Rgba<u8> {
    let mut h = user_id.wrapping_mul(0x9E37_79B9_7F4A_7C15);
    h ^= h >> 29;
    PALETTE[(h as usize) % PALETTE.len()]
}

fn is_emoji(c: char) -> bool {
    matches!(c as u32,
        0x1F000..=0x1FAFF | 0x2600..=0x27BF | 0x2B00..=0x2BFF |
        0xFE00..=0xFE0F | 0x200D | 0x20E3
    )
}

fn measure(
    scaled: &ab_glyph::PxScaleFont<FontRef<'static>>,
    emoji_scaled: &ab_glyph::PxScaleFont<FontRef<'static>>,
    text: &str,
) -> f32 {
    let mut w = 0.0f32;
    for c in text.chars() {
        if is_emoji(c) && emoji_scaled.glyph_id(c).0 != 0 {
            w += emoji_scaled.h_advance(emoji_scaled.glyph_id(c));
        } else {
            let id = scaled.glyph_id(c);
            w += scaled.h_advance(id);
        }
    }
    w
}

fn wrap_text(font: FontRef<'static>, emoji_font: FontRef<'static>, scale: f32, max_width: f32, text: &str) -> Vec<String> {
    let scaled = font.into_scaled(PxScale::from(scale));
    let emoji_scaled = emoji_font.into_scaled(PxScale::from(scale));
    let mut lines = Vec::new();
    for raw_line in text.split('\n') {
        if raw_line.is_empty() {
            lines.push(String::new());
            continue;
        }
        let mut line = String::new();
        for word in raw_line.split(' ') {
            let candidate = if line.is_empty() {
                word.to_string()
            } else {
                format!("{} {}", line, word)
            };
            if line.is_empty() || measure(&scaled, &emoji_scaled, &candidate) <= max_width {
                line = candidate;
            } else {
                if !line.is_empty() {
                    lines.push(std::mem::take(&mut line));
                }
                line = word.to_string();
                while measure(&scaled, &emoji_scaled, &line) > max_width && line.chars().count() > 1 {
                    let cut = line.char_indices().nth(1).map(|(i, _)| i).unwrap_or(line.len());
                    lines.push(line[..cut].to_string());
                    line = line[cut..].to_string();
                }
            }
        }
        lines.push(line);
    }
    lines
}

fn draw_text_line(
    img: &mut RgbaImage,
    font: FontRef<'static>,
    emoji_font: FontRef<'static>,
    scale: f32,
    color: Rgba<u8>,
    x: f32,
    baseline_y: f32,
    text: &str,
) {
    let scaled = font.into_scaled(PxScale::from(scale));
    let emoji_scaled = emoji_font.into_scaled(PxScale::from(scale));
    let mut pen_x = x;
    for c in text.chars() {
        if is_emoji(c) {
            let gid = emoji_scaled.glyph_id(c);
            if gid.0 != 0 {
                let glyph = gid.with_scale_and_position(PxScale::from(scale), point(pen_x, baseline_y));
                if let Some(outline) = emoji_scaled.outline_glyph(glyph) {
                    let bounds = outline.px_bounds();
                    outline.draw(|dx, dy, cov| {
                        let ix = bounds.min.x as i32 + dx as i32;
                        let iy = bounds.min.y as i32 + dy as i32;
                        let alpha = (cov.clamp(0.0, 1.0) * 255.0) as u8;
                        if alpha > 0 {
                            blend_pixel(img, ix, iy, color, alpha);
                        }
                    });
                }
                pen_x += emoji_scaled.h_advance(gid);
                continue;
            }
        }
        let gid = scaled.glyph_id(c);
        let glyph = gid.with_scale_and_position(PxScale::from(scale), point(pen_x, baseline_y));
        if let Some(outline) = scaled.outline_glyph(glyph) {
            let bounds = outline.px_bounds();
            outline.draw(|dx, dy, cov| {
                let ix = bounds.min.x as i32 + dx as i32;
                let iy = bounds.min.y as i32 + dy as i32;
                let alpha = (cov.clamp(0.0, 1.0) * 255.0) as u8;
                if alpha > 0 {
                    blend_pixel(img, ix, iy, color, alpha);
                }
            });
        }
        pen_x += scaled.h_advance(gid);
    }
}

fn blend_pixel(img: &mut RgbaImage, x: i32, y: i32, color: Rgba<u8>, alpha: u8) {
    let (w, h) = img.dimensions();
    if x < 0 || y < 0 || x as u32 >= w || y as u32 >= h {
        return;
    }
    let a = alpha as f32 / 255.0;
    let px = img.get_pixel_mut(x as u32, y as u32);
    for i in 0..3 {
        px[i] = (color[i] as f32 * a + px[i] as f32 * (1.0 - a)) as u8;
    }
}

fn fill_rounded_rect(
    img: &mut RgbaImage,
    x0: u32,
    y0: u32,
    x1: u32,
    y1: u32,
    radius: u32,
    color: Rgba<u8>,
) {
    let (w, h) = img.dimensions();
    if x0 > x1 || y0 > y1 || x0 >= w || y0 >= h {
        return;
    }
    let x1 = x1.min(w.saturating_sub(1));
    let y1 = y1.min(h.saturating_sub(1));
    let radius = radius.min((x1 - x0).min(y1 - y0) / 2);
    for y in y0..=y1 {
        for x in x0..=x1 {
            let cx = x.clamp(x0 + radius, x1 - radius);
            let cy = y.clamp(y0 + radius, y1 - radius);
            let dx = (x as f32 - cx as f32).abs();
            let dy = (y as f32 - cy as f32).abs();
            let rr = radius as f32;
            if dx * dx + dy * dy <= rr * rr {
                img.put_pixel(x, y, color);
            }
        }
    }
}

fn truncate(s: &str, max_chars: usize) -> String {
    if s.chars().count() <= max_chars {
        return s.to_string();
    }
    let mut out: String = s.chars().take(max_chars).collect();
    out.push('…');
    out
}

fn render_quote_image(messages: &[HistoryMessage]) -> Result<RgbaImage, String> {
    let font = FontRef::try_from_slice(FONT_DATA).map_err(|e| format!("font error: {}", e))?;
    let bold = font.clone();
    let emoji_font = font.clone();

    let max_text_width = (WIDTH - PAD * 2 - BUBBLE_PAD_X * 2 - ACCENT_W - 4) as f32;

    struct Row {
        name: String,
        lines: Vec<String>,
        color: Rgba<u8>,
    }

    let mut rows = Vec::with_capacity(messages.len());
    for m in messages {
        let text = truncate(&m.text, MAX_TEXT_CHARS);
        let name = truncate(if m.user_name.is_empty() { "Unknown" } else { &m.user_name }, 30);
        let lines = wrap_text(font.clone(), emoji_font.clone(), TEXT_SIZE, max_text_width, &text);
        rows.push(Row {
            name,
            lines,
            color: user_color(m.user_id),
        });
    }

    let bold_scaled = bold.clone().into_scaled(PxScale::from(NAME_SIZE));
    let name_h = bold_scaled.ascent() - bold_scaled.descent();
    let text_scaled = font.clone().into_scaled(PxScale::from(TEXT_SIZE));
    let line_h = text_scaled.ascent() - text_scaled.descent();

    let mut bubble_heights: Vec<u32> = Vec::with_capacity(rows.len());
    for row in &rows {
        let mut h = BUBBLE_PAD_Y as f32 + name_h + NAME_TO_TEXT_GAP;
        if !row.lines.is_empty() {
            h += line_h * row.lines.len() as f32;
        }
        h += BUBBLE_PAD_Y as f32;
        bubble_heights.push(h.ceil() as u32);
    }

    let total_h = PAD * 2
        + bubble_heights.iter().sum::<u32>()
        + GAP * bubble_heights.len().saturating_sub(1) as u32;
    let total_h = total_h.max(80);

    let mut img = RgbaImage::from_pixel(WIDTH, total_h, BG);

    let mut y = PAD as f32;
    for (row, bh) in rows.iter().zip(bubble_heights.iter()) {
        let bubble_x0 = PAD;
        let bubble_x1 = WIDTH - PAD;
        let bubble_y0 = y.ceil() as u32;
        let bubble_y1 = bubble_y0 + bh - 1;

        fill_rounded_rect(&mut img, bubble_x0, bubble_y0, bubble_x0 + ACCENT_W - 1, bubble_y1, 4, row.color);
        fill_rounded_rect(&mut img, bubble_x0 + ACCENT_W, bubble_y0, bubble_x1, bubble_y1, RADIUS, BUBBLE);

        let text_x = (bubble_x0 + ACCENT_W + BUBBLE_PAD_X) as f32;
        let name_baseline = (bubble_y0 + BUBBLE_PAD_Y) as f32 + bold_scaled.ascent();
        draw_text_line(&mut img, bold.clone(), emoji_font.clone(), NAME_SIZE, row.color, text_x, name_baseline, &row.name);

        let mut tb = (bubble_y0 + BUBBLE_PAD_Y) as f32 + name_h + NAME_TO_TEXT_GAP + text_scaled.ascent();
        for line in &row.lines {
            draw_text_line(&mut img, font.clone(), emoji_font.clone(), TEXT_SIZE, TEXT_WHITE, text_x, tb, line);
            tb += line_h;
        }

        y += *bh as f32 + GAP as f32;
    }

    Ok(img)
}

const STICKER_SIZE: u32 = 512;

pub fn render_quote(messages: &[HistoryMessage]) -> Result<Vec<u8>, String> {
    let img = render_quote_image(messages)?;
    let (w, h) = img.dimensions();
    let mut buf = Vec::new();
    image::codecs::png::PngEncoder::new(&mut buf)
        .write_image(&img.into_raw(), w, h, image::ExtendedColorType::Rgba8)
        .map_err(|e| format!("png encode error: {}", e))?;
    Ok(buf)
}

pub fn render_quote_sticker(messages: &[HistoryMessage]) -> Result<Vec<u8>, String> {
    let img = render_quote_image(messages)?;
    let (w, h) = img.dimensions();
    let scale = ((STICKER_SIZE as f32) / (w as f32))
        .min((STICKER_SIZE as f32) / (h as f32))
        .min(1.0);
    let nw = ((w as f32) * scale).round().max(1.0) as u32;
    let nh = ((h as f32) * scale).round().max(1.0) as u32;
    let resized = image::imageops::resize(&img, nw, nh, image::imageops::FilterType::Lanczos3);
    let mut canvas = RgbaImage::from_pixel(STICKER_SIZE, STICKER_SIZE, BG);
    let ox = (STICKER_SIZE - nw) / 2;
    let oy = (STICKER_SIZE - nh) / 2;
    image::imageops::overlay(&mut canvas, &resized, ox as i64, oy as i64);

    let mut buf = Vec::new();
    image::codecs::webp::WebPEncoder::new_lossless(&mut buf)
        .write_image(&canvas.into_raw(), STICKER_SIZE, STICKER_SIZE, image::ExtendedColorType::Rgba8)
        .map_err(|e| format!("webp encode error: {}", e))?;
    Ok(buf)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn render_sample_quote() {
        let msgs = vec![
            HistoryMessage {
                message_id: 1,
                user_id: 111,
                user_name: "@luffy".into(),
                text: "I'm gonna be the King of the Pirates!".into(),
                date: 1,
            },
            HistoryMessage {
                message_id: 2,
                user_id: 222,
                user_name: "@zoro".into(),
                text: "I got lost again... where is the ship?".into(),
                date: 2,
            },
            HistoryMessage {
                message_id: 3,
                user_id: 333,
                user_name: "@nami".into(),
                text: "You idiots! We have to pay the crew's debts — all 300 million beri!".into(),
                date: 3,
            },
        ];
        let bytes = render_quote(&msgs).unwrap();
        std::fs::write("/tmp/opencode/quote_test.png", &bytes).unwrap();
        assert!(bytes.len() > 1000);

        let sticker = render_quote_sticker(&msgs).unwrap();
        std::fs::write("/tmp/opencode/quote_test.webp", &sticker).unwrap();
        assert_eq!(&sticker[..4], b"RIFF", "sticker must be a valid webp");
        assert_eq!(&sticker[8..12], b"WEBP");
    }

    #[test]
    fn render_emoji_and_multi_message() {
        let msgs = vec![
            HistoryMessage {
                message_id: 1,
                user_id: 111,
                user_name: "@luffy".into(),
                text: "Let's go!! 🚀⚓🏴‍☠️".into(),
                date: 1,
            },
            HistoryMessage {
                message_id: 2,
                user_id: 222,
                user_name: "@chopper".into(),
                text: "I'm not a raccoon dog!! 🦌😤".into(),
                date: 2,
            },
            HistoryMessage {
                message_id: 3,
                user_id: 333,
                user_name: "@robin".into(),
                text: "The answer is always here. 📚".into(),
                date: 3,
            },
        ];
        let sticker = render_quote_sticker(&msgs).unwrap();
        std::fs::write("/tmp/opencode/quote_emoji.webp", &sticker).unwrap();
        assert_eq!(&sticker[..4], b"RIFF", "sticker must be a valid webp");
        assert_eq!(&sticker[8..12], b"WEBP");
        assert!(sticker.len() > 1000);
    }

    #[test]
    fn parse_quote_count_variants() {
        assert_eq!(parse_quote_count("/q"), 1);
        assert_eq!(parse_quote_count("/q2"), 2);
        assert_eq!(parse_quote_count("/q3"), 3);
        assert_eq!(parse_quote_count("/q 2"), 2);
        assert_eq!(parse_quote_count("/q10"), MAX_QUOTE_MESSAGES);
        assert_eq!(parse_quote_count("/q 99"), MAX_QUOTE_MESSAGES);
        assert_eq!(parse_quote_count("/q2@bot"), 2);
        assert_eq!(parse_quote_count(""), 1);
    }
}
