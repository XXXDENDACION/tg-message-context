from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str
    source_chat_id: int
    target_channel_id: int

    # Google Gemini
    gemini_api_key: str

    # Database
    database_url: str = "sqlite+aiosqlite:///data/bot.db"

    # Context
    context_messages_count: int = 20


settings = Settings()  # type: ignore[call-arg]
