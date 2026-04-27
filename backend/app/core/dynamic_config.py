import logging
import asyncio
from typing import Any
from app.infrastructure.database import get_pool
from app.core.encryption import decrypt_value, encrypt_value

logger = logging.getLogger("rag.dynamic_config")

# In-memory cache for settings
_CONFIG_CACHE: dict[str, Any] = {}
_LAST_FETCH = 0
CACHE_TTL = 60  # seconds

SENSITIVE_KEYS = {"openai_api_key", "anthropic_api_key", "vector_db_api_key", "gemini_api_key"}

async def get_config_value(key: str, default: Any = None) -> Any:
    """Get a configuration value from the DB, with fallback to default."""
    global _LAST_FETCH
    
    import time
    now = time.time()
    
    # Refresh cache if empty or expired
    if not _CONFIG_CACHE or (now - _LAST_FETCH) > CACHE_TTL:
        await refresh_config_cache()
        _LAST_FETCH = now
        
    return _CONFIG_CACHE.get(key, default)

async def set_config_values(settings_list: list[dict[str, Any]]) -> None:
    """
    Update multiple settings in the database and refresh the cache.
    Each item in settings_list should have 'key' and 'value'.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for item in settings_list:
                key = item["key"]
                value = str(item["value"])
                is_encrypted = False
                
                # Encrypt sensitive keys
                if key in SENSITIVE_KEYS and value and "*" not in value:
                    value = encrypt_value(value)
                    is_encrypted = True
                elif key in SENSITIVE_KEYS and "*" in value:
                    # Skip masked values
                    continue
                
                await conn.execute(
                    """
                    INSERT INTO system_settings (key, value, is_encrypted, updated_at)
                    VALUES ($1, $2, $3, NOW())
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        is_encrypted = EXCLUDED.is_encrypted,
                        updated_at = EXCLUDED.updated_at
                    """,
                    key, value, is_encrypted
                )
    
    # Refresh cache immediately
    await refresh_config_cache()

async def refresh_config_cache():
    """Fetch all settings from DB and populate the cache."""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            # Check if table exists first to avoid crash during first-time init
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'system_settings')"
            )
            if not table_exists:
                logger.warning("system_settings table does not exist yet. Skipping cache refresh.")
                return

            rows = await conn.fetch("SELECT key, value, is_encrypted FROM system_settings")
            
        new_cache = {}
        for row in rows:
            key = row["key"]
            value = row["value"]
            if row["is_encrypted"]:
                value = decrypt_value(value)
            
            # Cast numeric values
            if value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit():
                try:
                    value = float(value)
                except ValueError:
                    pass
            
            new_cache[key] = value
            
        global _CONFIG_CACHE
        _CONFIG_CACHE = new_cache
        logger.info(f"Dynamic config cache refreshed: {len(_CONFIG_CACHE)} keys.")
    except Exception as e:
        logger.error(f"Failed to refresh dynamic config cache: {e}")
