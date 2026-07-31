use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Update {
    pub update_id: u64,
    pub message: Option<Message>,
    pub callback_query: Option<CallbackQuery>,
    pub my_chat_member: Option<ChatMemberUpdated>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Message {
    pub message_id: u64,
    pub from: Option<User>,
    pub chat: Chat,
    pub date: u64,
    pub text: Option<String>,
    pub entities: Option<Vec<MessageEntity>>,
    pub reply_to_message: Option<Box<Message>>,
    pub new_chat_members: Option<Vec<User>>,
    pub left_chat_member: Option<User>,
    pub photo: Option<Vec<PhotoSize>>,
    pub video: Option<serde_json::Value>,
    pub animation: Option<serde_json::Value>,
    pub sticker: Option<serde_json::Value>,
    pub document: Option<serde_json::Value>,
    pub voice: Option<serde_json::Value>,
    pub audio: Option<serde_json::Value>,
    pub video_note: Option<serde_json::Value>,
    pub poll: Option<serde_json::Value>,
    pub forward_date: Option<u64>,
    pub forward_from: Option<User>,
}

impl Message {
    pub fn text(&self) -> Option<&str> {
        self.text.as_deref()
    }

    pub fn from(&self) -> Option<&User> {
        self.from.as_ref()
    }

    pub fn id(&self) -> u64 {
        self.message_id
    }

    pub fn reply_to_message(&self) -> Option<&Message> {
        self.reply_to_message.as_deref()
    }

    pub fn entities(&self) -> Option<&Vec<MessageEntity>> {
        self.entities.as_ref()
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct User {
    pub id: u64,
    pub is_bot: bool,
    pub first_name: String,
    pub username: Option<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Chat {
    pub id: i64,
    #[serde(rename = "type")]
    pub type_: String,
    pub title: Option<String>,
    pub username: Option<String>,
}

impl Chat {
    pub fn is_group(&self) -> bool {
        self.type_ == "group"
    }

    pub fn is_supergroup(&self) -> bool {
        self.type_ == "supergroup"
    }

    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct MessageEntity {
    #[serde(rename = "type")]
    pub type_: String,
    pub offset: u64,
    pub length: u64,
    pub user: Option<User>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct CallbackQuery {
    pub id: String,
    pub from: User,
    pub message: Option<Message>,
    pub data: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct InlineKeyboardButton {
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub callback_data: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
}

#[derive(Clone, Debug, Serialize)]
pub struct InlineKeyboardMarkup {
    pub inline_keyboard: Vec<Vec<InlineKeyboardButton>>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ChatMemberUpdated {
    pub chat: Chat,
    pub from: User,
    pub date: u64,
    pub old_chat_member: ChatMember,
    pub new_chat_member: ChatMember,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct PhotoSize {
    pub file_id: String,
    pub width: u64,
    pub height: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ChatMember {
    pub user: User,
    pub status: String,
}

impl ChatMember {
    pub fn status(&self) -> &str {
        &self.status
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct ChatPermissions {
    pub can_send_messages: Option<bool>,
    pub can_send_media_messages: Option<bool>,
    pub can_send_polls: Option<bool>,
    pub can_send_other_messages: Option<bool>,
    pub can_add_web_page_previews: Option<bool>,
    pub can_change_info: Option<bool>,
    pub can_invite_users: Option<bool>,
    pub can_pin_messages: Option<bool>,
    pub can_manage_topics: Option<bool>,
}

impl ChatPermissions {
    pub fn empty() -> Self {
        Self {
            can_send_messages: Some(false),
            can_send_media_messages: Some(false),
            can_send_polls: Some(false),
            can_send_other_messages: Some(false),
            can_add_web_page_previews: Some(false),
            can_change_info: Some(false),
            can_invite_users: Some(false),
            can_pin_messages: Some(false),
            can_manage_topics: Some(false),
        }
    }

    pub fn all() -> Self {
        Self {
            can_send_messages: Some(true),
            can_send_media_messages: Some(true),
            can_send_polls: Some(true),
            can_send_other_messages: Some(true),
            can_add_web_page_previews: Some(true),
            can_change_info: Some(true),
            can_invite_users: Some(true),
            can_pin_messages: Some(true),
            can_manage_topics: Some(true),
        }
    }
}
