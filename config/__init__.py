"""
Unified config — backward compatible with old config.py imports.
All existing imports like `from config import DEBUG_MODE` still work.
"""

import os
from importlib import import_module
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# =========================
# Legacy (from config.py)
# =========================

PDFS_DIR = "pdfs"
DEBUG_MODE = False
DOCUMENT_HINTS = {
    "Tesla": [
        "tesla",
        "robotaxi",
        "cybercab",
        "optimus",
        "fsd",
        "supercharger",
        "megapack",
    ],
    "NVIDIA": [
        "nvidia",
        "blackwell",
        "cuda",
        "dgx",
        "nvlink",
        "ai factory",
        "grace",
        "hopper",
    ],
    "Apple": [
        "apple",
        "apple intelligence",
        "vision pro",
        "iphone",
        "ipad",
        "mac",
        "services",
        "app store",
    ],
}

CACHE_DIR = "cache"
TOP_K = 4
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CACHE_VERSION = "1.8"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# =========================
# New (V7.3 — env-driven)
# =========================

APP_ENV = os.environ.get("APP_ENV", "development")
APP_VERSION = os.environ.get("APP_VERSION", "7.3.3")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

ROOT_DIR = Path(__file__).resolve().parent.parent

CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", ROOT_DIR / "chroma_db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", ROOT_DIR / "storage" / "uploads"))
PDF_DIR = Path(os.environ.get("PDF_DIR", ROOT_DIR / "storage" / "pdfs"))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# Backward compatibility for old env vars
if not os.environ.get("LLM_MODEL") and os.environ.get("DEEPSEEK_MODEL"):
    os.environ["LLM_MODEL"] = os.environ["DEEPSEEK_MODEL"]

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

# =========================
# UI (V7.3 Phase 2.2)
# =========================


# =========================
# LLM (V5 Phase 1 — Provider abstraction)
# =========================
_llm_config = import_module(".llm", __package__)
LLM_PROVIDER = _llm_config.LLM_PROVIDER
LLM_MODEL = _llm_config.LLM_MODEL
LLM_API_KEY = _llm_config.LLM_API_KEY
LLM_BASE_URL = _llm_config.LLM_BASE_URL
LLM_TEMPERATURE = _llm_config.LLM_TEMPERATURE
LLM_MAX_TOKENS = _llm_config.LLM_MAX_TOKENS
LLM_TIMEOUT = _llm_config.LLM_TIMEOUT
LLM_STREAM = _llm_config.LLM_STREAM
DEEPSEEK_MODEL = _llm_config.DEEPSEEK_MODEL
DEEPSEEK_BASE_URL = _llm_config.DEEPSEEK_BASE_URL
GEMINI_API_KEY = _llm_config.GEMINI_API_KEY
GEMINI_MODEL = _llm_config.GEMINI_MODEL

_ui_config = import_module(".ui", __package__)
_ui_exports = getattr(
    _ui_config,
    "__all__",
    (name for name in vars(_ui_config) if not name.startswith("_")),
)
for _name in _ui_exports:
    globals()[_name] = getattr(_ui_config, _name)

__all__ = [
    "PDFS_DIR",
    "DEBUG_MODE",
    "DOCUMENT_HINTS",
    "CACHE_DIR",
    "TOP_K",
    "EMBEDDING_MODEL",
    "CACHE_VERSION",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "APP_ENV",
    "APP_VERSION",
    "LOG_LEVEL",
    "ROOT_DIR",
    "CHROMA_PATH",
    "UPLOAD_DIR",
    "PDF_DIR",
    "DEEPSEEK_API_KEY",
    "REDIS_HOST",
    "REDIS_PORT",
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "LLM_TIMEOUT",
    "LLM_STREAM",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_BASE_URL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
]
