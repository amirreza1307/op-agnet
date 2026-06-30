import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from api.errors import ServiceUnavailableError
from setup.config import config


class ChannelCrypto:
    @staticmethod
    def _fernet() -> MultiFernet:
        raw_keys = str(config.CHANNEL_TOKEN_ENCRYPTION_KEY or "")
        try:
            keys = [
                key.strip().encode("ascii")
                for key in raw_keys.split(",")
                if key.strip()
            ]
            if not keys:
                raise ServiceUnavailableError(
                    "CHANNEL_TOKEN_ENCRYPTION_KEY is required for channel operations"
                )
            return MultiFernet([Fernet(key) for key in keys])
        except ServiceUnavailableError:
            raise
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            raise ServiceUnavailableError(
                "CHANNEL_TOKEN_ENCRYPTION_KEY is not a valid Fernet key"
            ) from exc

    @classmethod
    def encrypt(cls, value: str) -> str:
        return cls._fernet().encrypt(value.encode("utf-8")).decode("ascii")

    @classmethod
    def decrypt(cls, value: str) -> str:
        try:
            return cls._fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError) as exc:
            raise ServiceUnavailableError(
                "Channel credentials cannot be decrypted with the configured key"
            ) from exc

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_webhook_secret() -> str:
        # token_urlsafe only uses characters accepted by Telegram secret_token.
        return secrets.token_urlsafe(32)

    @staticmethod
    def token_hint(token: str) -> str:
        if len(token) <= 8:
            return "****"
        return f"{token[:4]}…{token[-4:]}"
