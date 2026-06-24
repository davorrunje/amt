from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TURING_",
        env_file=".env",
        extra="ignore",
        protected_namespaces=(),
    )

    model: str = "gemini/gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 1024
