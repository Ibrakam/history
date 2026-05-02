from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "History AI"
    admin_username: str = "admin"
    admin_password: str = "admin123"
    session_secret: str = "change-me"
    openai_api_key: str | None = None
    openai_model: str = "llama-3.3-70b-versatile"
    openai_image_model: str = "gpt-image-1"
    openai_base_url: str = "https://api.groq.com/openai/v1"
    ai_request_timeout: float = 120.0
    use_demo_ai: bool = False
    enable_external_media_search: bool = True
    enable_source_materials: bool = True
    source_first_generation: bool = False
    source_material_limit: int = 10
    source_material_min_score: float = 4.0
    frontend_origin: str = "http://localhost:5173"
    database_url: str = "sqlite:///./history.db"
    wikimedia_api_url: str = "https://commons.wikimedia.org/w/api.php"
    upload_dir: Path = ROOT_DIR / "backend" / "uploads"
    upload_max_bytes: int = 8 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        source_priority = os.getenv("SETTINGS_SOURCE_PRIORITY", "dotenv_first").lower()
        if source_priority == "env_first":
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )

        # Prefer the project's .env over inherited shell variables so local
        # key rotation is applied predictably after a backend restart.
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
