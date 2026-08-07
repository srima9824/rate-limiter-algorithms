from pydantic_settings import BaseSettings, SettingsConfigDict

# To instantiate and Type Validate Global Settings from .env file to be used by app
class Settings(BaseSettings):
    max_tokens: int
    refill_rate: float
    tokens_per_request: int = 1
    bucket_cleanup_interval: int = 300
    bucket_expiry_seconds: int = 1800
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()
