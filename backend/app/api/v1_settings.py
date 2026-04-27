import logging
from fastapi import APIRouter, HTTPException
from app.infrastructure.database import get_pool
from app.domain.rag import SystemSetting, SettingsResponse, SettingsUpdate
from app.core.encryption import encrypt_value, decrypt_value, mask_value
from app.core.dynamic_config import get_config_value, set_config_values

logger = logging.getLogger("rag.api.settings")
router = APIRouter()

SENSITIVE_KEYS = {"openai_api_key", "anthropic_api_key", "vector_db_api_key", "gemini_api_key"}

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Fetch all system settings from the database."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value, is_encrypted, updated_at FROM system_settings")
        
    settings = []
    for row in rows:
        key = row["key"]
        value = row["value"]
        is_encrypted = row["is_encrypted"]
        
        # If it's a sensitive key, mask it for the UI
        if key in SENSITIVE_KEYS:
            if is_encrypted:
                value = decrypt_value(value)
            value = mask_value(value)
        
        settings.append(SystemSetting(
            key=key,
            value=value,
            is_encrypted=is_encrypted,
            updated_at=row["updated_at"]
        ))
    
    return SettingsResponse(settings=settings)

@router.post("/settings", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    """Update system settings in the database."""
    # Convert list of SystemSetting to list of dicts for set_config_values
    settings_list = [
        {"key": s.key, "value": s.value}
        for s in update.settings
    ]
    
    await set_config_values(settings_list)
    
    return await get_settings()
