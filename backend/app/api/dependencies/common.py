from app.core.config import Settings, settings


async def get_settings() -> Settings:
    return settings
