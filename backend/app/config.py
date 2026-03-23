from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./data/brain_tool.db"
    jwt_secret: str = "change_me"
    jwt_expire_minutes: int = 10080
    app_timezone: str = "Asia/Shanghai"

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-5.3-codex"
    llm_timeout_seconds: int = 60
    classification_confidence_threshold: float = 0.7

    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = True
    smtp_from_email: str = ""
    smtp_from_name: str = "Second Brain Tool"

    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def parsed_cors_allow_origins(self) -> list[str]:
        return [i.strip() for i in self.cors_allow_origins.split(",") if i.strip()]


settings = Settings()
