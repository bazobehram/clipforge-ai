import os
from typing import Optional

def load_env_file(filepath: str = ".env"):
    """Basit ve bağımlılıksız .env dosya okuyucu"""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val

load_env_file()

class Settings:
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")

    # Güvenlik & Giriş Şifresi
    AUTH_PASSWORD: str = os.getenv("AUTH_PASSWORD", "clipforge2026._")
    AUTH_SECRET: str = os.getenv("AUTH_SECRET", "clipforge_secret_key_2026")

    # LLM Settings
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Whisper Settings (base: hızlı ama zayıf, small: dengeli/hızlı, large-v3-turbo: amiral gemisi/yüksek doğruluk)
    WHISPER_TYPE: str = os.getenv("WHISPER_TYPE", "local")
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "large-v3-turbo")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Processing Settings
    VERTICAL_MODE: str = os.getenv("VERTICAL_MODE", "blur_background")
    MAX_CLIPS: int = int(os.getenv("MAX_CLIPS", "4"))
    CANDIDATES_COUNT: int = int(os.getenv("CANDIDATES_COUNT", "10"))
    MIN_CLIP_DURATION: int = int(os.getenv("MIN_CLIP_DURATION", "30"))
    MAX_CLIP_DURATION: int = int(os.getenv("MAX_CLIP_DURATION", "90"))

    # Paths
    DATA_DIR: str = os.getenv("DATA_DIR", "./data")
    DOWNLOADS_DIR: str = os.path.join(DATA_DIR, "downloads")
    OUTPUT_DIR: str = os.path.join(DATA_DIR, "output")
    TEMP_DIR: str = os.path.join(DATA_DIR, "temp")
    HISTORY_FILE: str = os.path.join(DATA_DIR, "history.json")

settings = Settings()

# Ensure directories exist
os.makedirs(settings.DOWNLOADS_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)
