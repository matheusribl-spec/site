import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "troque-esta-chave-por-uma-chave-segura")
    DB_USE_SQLITE: bool = os.getenv("DB_USE_SQLITE", "1") == "1"
    SQLITE_PATH: Path = Path(os.getenv("SQLITE_PATH", str(BASE_DIR / "data.sqlite")))
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "mandato")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    UPLOAD_FOLDER: Path = Path(os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "static" / "uploads")))
    ALLOWED_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "gif"})
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_REFRESH_EACH_REQUEST: bool = True
    SESSION_COOKIE_SECURE: bool = os.getenv("FLASK_ENV", "development") == "production"
    SCRAPER_TIMEOUT: int = int(os.getenv("SCRAPER_TIMEOUT", "12"))
