use crate::utils::escape_md_v2;

pub fn ban_msg(name: &str) -> String {
    format!("🏴‍☠️ {} walked the plank.", escape_md_v2(name))
}

pub fn mute_msg(name: &str) -> String {
    format!("🔇 {} silenced — Sea Prism cuffs on.", escape_md_v2(name))
}

pub fn kick_msg(name: &str) -> String {
    format!("🚪 {} tossed off the ship.", escape_md_v2(name))
}

pub fn warn_msg(name: &str, count: i64, threshold: i64, reason: &str) -> String {
    format!(
        "⚠️ {} marked by the log pose. ({}/{})\nReason: {}",
        escape_md_v2(name),
        count,
        threshold,
        escape_md_v2(reason)
    )
}

pub fn auto_ban_msg(name: &str, count: i64, reason: &str) -> String {
    format!(
        "🚫 {} auto-banned (exceeded {} warnings) — {}",
        escape_md_v2(name),
        count,
        escape_md_v2(reason)
    )
}

pub fn swear_detected(word: &str) -> String {
    format!(
        "🍶 Watch yer tongue, or Zoro's swords come out. ({})",
        escape_md_v2(word)
    )
}

pub fn welcome_set() -> String {
    "📜 New crew banner nailed to the mast.".to_string()
}

pub fn admin_denied() -> String {
    "🚫 Only Straw Hat officers give that order.".to_string()
}

pub fn sudo_denied() -> String {
    "☠️ Only the Captain (Roger-tier) can do this.".to_string()
}

pub fn tmute_msg(name: &str, human_duration: &str) -> String {
    format!(
        "🔇 {} silenced — Sea Prism cuffs on for {}.",
        escape_md_v2(name),
        escape_md_v2(human_duration)
    )
}

pub fn tban_msg(name: &str, human_duration: &str) -> String {
    format!(
        "🏴‍☠️ {} walked the plank for {}.",
        escape_md_v2(name),
        escape_md_v2(human_duration)
    )
}
