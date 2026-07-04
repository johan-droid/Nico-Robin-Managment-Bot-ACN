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
        self._key_rotation_keys: list[Fernet] = []
        if key:
            try:
                self._fernet = Fernet(key.encode("utf-8"))
                # Support for key rotation - can add previous keys here
                self._key_rotation_keys.append(self._fernet)
            except (ValueError, TypeError) as e:
                from src.bot.services.security_logger import SecurityLogger
                import asyncio
                asyncio.create_task(SecurityLogger.log_event(
                    "invalid_encryption_key",
                    severity="HIGH",
                    details={"error": str(e)}
                ))
                raise ValueError("Invalid encryption key - potential security issue") from e

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def add_rotation_key(self, key: str) -> None:
        """Add a previous key for decryption during key rotation"""
        try:
            fernet = Fernet(key.encode("utf-8"))
            self._key_rotation_keys.append(fernet)
        except (ValueError, TypeError):
            pass  # Invalid key, ignore

    def encrypt_text(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if not self._fernet:
            from src.bot.services.security_logger import SecurityLogger
            import asyncio
            asyncio.create_task(SecurityLogger.log_event(
                "encryption_disabled",
                severity="MEDIUM",
                details={"operation": "encrypt_text"}
            ))
            return value

        # Input validation to prevent encryption of sensitive patterns
        if any(pattern in value for pattern in ["password", "secret", "token"]):
            from src.bot.services.security_logger import SecurityLogger
            import asyncio
            asyncio.create_task(SecurityLogger.log_event(
                "sensitive_data_encryption_attempt",
                severity="HIGH",
                details={"data_type": "text"}
            ))

        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_text(self, value: str | None) -> str | None:
        if value is None or value == "":
            return value
        if not self._fernet:
            return value

        # Try current key first
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            # Try rotation keys for backward compatibility
            for fernet in self._key_rotation_keys:
                try:
                    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
                except (InvalidToken, ValueError):
                    continue

        # Log failed decryption attempts
        from src.bot.services.security_logger import SecurityLogger
        import asyncio
        asyncio.create_task(SecurityLogger.log_event(
            "decryption_failed",
            severity="MEDIUM",
            details={"data_length": len(value)}
        ))

        return value

    def encrypt_mapping(self, value: dict[str, Any] | None) -> str | None:
        if value is None:
            return None

        # Redact sensitive keys before encryption
        sensitive_keys = {"password", "secret", "token", "api_key"}
        sanitized = {k: "[REDACTED]" if k.lower() in sensitive_keys else v
                    for k, v in value.items()}

        return self.encrypt_text(json.dumps(sanitized, ensure_ascii=False))

    def decrypt_mapping(self, value: str | None) -> dict[str, Any]:
        payload = self.decrypt_text(value)
        if not payload:
            return {}

        try:
            loaded = json.loads(payload)
            if not isinstance(loaded, dict):
                return {"raw": payload}
            return loaded
        except json.JSONDecodeError:
            from src.bot.services.security_logger import SecurityLogger
            import asyncio
            asyncio.create_task(SecurityLogger.log_event(
                "decryption_json_error",
                severity="LOW",
                details={"data_length": len(value) if value else 0}
            ))
            return {"raw": payload}

    def mask_secret(self, value: str, visible: int = 4) -> str:
        if len(value) <= visible:
            return "*" * len(value)
        return f"{value[:visible]}***"

    def validate_key_strength(self, key: str) -> bool:
        """Validate that the encryption key meets security standards"""
        if not key or len(key) < 44:  # Fernet keys are base64 encoded 32-byte keys
            return False
        try:
            # Test that the key can actually be used
            test_fernet = Fernet(key.encode("utf-8"))
            test_fernet.encrypt(b"test")
            return True
        except (ValueError, TypeError):
            return False


@lru_cache(maxsize=1)
def get_crypto_service() -> CryptoService:
    return CryptoService(settings.data_encryption_key)


def generate_fernet_key() -> str:
    return base64.urlsafe_b64encode(Fernet.generate_key()).decode("utf-8")
