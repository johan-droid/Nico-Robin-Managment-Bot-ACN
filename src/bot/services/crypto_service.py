from __future__ import annotations

import base64
import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from src.bot.config import settings


class CryptoService:
    def __init__(self, key: str | None) -> None:
        self._fernet: Fernet | None = None
        if key:
            self._fernet = Fernet(key.encode("utf-8"))

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt_text(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if not self._fernet:
            return value
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_text(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if not self._fernet:
            return value
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            return value

    def encrypt_mapping(self, value: dict[str, Any] | None) -> str | None:
        if value is None:
            return None
        return self.encrypt_text(json.dumps(value, ensure_ascii=False))

    def decrypt_mapping(self, value: str | None) -> dict[str, Any]:
        payload = self.decrypt_text(value)
        if not payload:
            return {}
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload}
        return loaded if isinstance(loaded, dict) else {"raw": loaded}

    def mask_secret(self, value: str, visible: int = 4) -> str:
        if len(value) <= visible:
            return "*" * len(value)
        return f"{value[:visible]}***"


@lru_cache(maxsize=1)
def get_crypto_service() -> CryptoService:
    return CryptoService(settings.data_encryption_key)


def generate_fernet_key() -> str:
    return base64.urlsafe_b64encode(Fernet.generate_key()).decode("utf-8")
