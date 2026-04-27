from cryptography.fernet import Fernet
from app.core.config import settings

def encrypt_value(value: str) -> str:
    """Encrypt a string using the ENCRYPTION_KEY."""
    if not settings.encryption_key:
        return value
    f = Fernet(settings.encryption_key.encode())
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a string using the ENCRYPTION_KEY."""
    if not settings.encryption_key:
        return encrypted_value
    try:
        f = Fernet(settings.encryption_key.encode())
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # If decryption fails, return as is (might not be encrypted)
        return encrypted_value

def mask_value(value: str) -> str:
    """Mask a sensitive value (e.g., API key)."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]
