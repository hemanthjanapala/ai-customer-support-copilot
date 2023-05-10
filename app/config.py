from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ai-customer-support-copilot"
    version: str = "0.1.0"

    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"

    database_url: str = ""

    api_key: str = "dev-key-change-me"

    history_window: int = 10
    llm_timeout_s: int = 10
    rate_limit_per_minute: int = 30
    log_level: str = "INFO"


settings = Settings()
