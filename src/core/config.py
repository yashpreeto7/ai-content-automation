import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base project paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output"
DEFAULT_ASSETS_DIR = ROOT_DIR / "assets"
DEFAULT_TEMPLATES_DIR = ROOT_DIR / "templates"
DEFAULT_PROJECTS_DIR = ROOT_DIR / "projects"
DEFAULT_DB_PATH = ROOT_DIR / "projects.db"

class Settings(BaseSettings):
    # Active AI Provider: "gemini" or "ollama"
    ai_provider: str = "gemini"

    # Gemini Cloud Provider
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

    # Ollama Local Provider
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = "llava"

    # Speech Synthesis & Transcription
    default_voice: str = "hi-IN-MadhurNeural"
    faster_whisper_model: str = "base"
    faster_whisper_device: str = "cpu"  # "cuda" if available, else "cpu"
    faster_whisper_compute: str = "int8"

    # Audio & Video Editing Defaults
    silence_threshold_ms: int = 800
    ducking_db: float = -12.0
    default_aspect_ratio: str = "9:16"
    default_style: str = "cinematic"
    log_level: str = "INFO"

    # Publishing Credentials (Optional)
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_redirect_uri: str = "http://localhost:8765/api/publish/youtube/callback"
    instagram_access_token: Optional[str] = None
    instagram_account_id: Optional[str] = None

    # Directory Paths
    base_dir: Path = ROOT_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    assets_dir: Path = DEFAULT_ASSETS_DIR
    templates_dir: Path = DEFAULT_TEMPLATES_DIR
    projects_dir: Path = DEFAULT_PROJECTS_DIR
    uploads_dir: Path = ROOT_DIR / "uploads"
    db_path: Path = DEFAULT_DB_PATH

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
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
