import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base project paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output"
DEFAULT_ASSETS_DIR = ROOT_DIR / "assets"
DEFAULT_TEMPLATES_DIR = ROOT_DIR / "templates"

class Settings(BaseSettings):
    # API Keys
    gemini_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    runway_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    fal_key: Optional[str] = None

    # Pipeline Defaults
    default_aspect_ratio: str = "9:16"
    default_voice: str = "en-US-ChristopherNeural"
    default_style: str = "cinematic"
    log_level: str = "INFO"

    # Directory Paths
    output_dir: Path = DEFAULT_OUTPUT_DIR
    assets_dir: Path = DEFAULT_ASSETS_DIR
    templates_dir: Path = DEFAULT_TEMPLATES_DIR

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        (self.assets_dir / "fonts").mkdir(exist_ok=True)
        (self.assets_dir / "music").mkdir(exist_ok=True)
        (self.assets_dir / "sfx").mkdir(exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
