"""
Unified config — backward compatible with old config.py imports.
All existing imports like `from config import DEBUG_MODE` still work.
"""

import os
from pathlib import Path

# =========================
# Legacy (from config.py)
# =========================

PDFS_DIR = "pdfs"
DEBUG_MODE = False
DOCUMENT_HINTS = {
    "Tesla": [
        "tesla", "robotaxi", "cybercab", "optimus", "fsd",
        "supercharger", "megapack",
    ],
    "NVIDIA": [
        "nvidia", "blackwell", "cuda", "dgx", "nvlink",
        "ai factory", "grace", "hopper",
    ],
    "Apple": [
        "apple", "apple intelligence", "vision pro", "iphone",
        "ipad", "mac", "services", "app store",
    ],
}

CACHE_DIR = "cache"
TOP_K = 4
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CACHE_VERSION = "1.8"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
LLM_TEMPERATURE = 0.2
LLM_MAX_TOKENS = 1000

# =========================
# New (V4.3 — env-driven)
# =========================

APP_ENV = os.environ.get("APP_ENV", "development")
APP_VERSION = os.environ.get("APP_VERSION", "4.3.0")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

ROOT_DIR = Path(__file__).resolve().parent.parent

CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", ROOT_DIR / "chroma_db"))
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", ROOT_DIR / "storage" / "uploads"))
PDF_DIR = Path(os.environ.get("PDF_DIR", ROOT_DIR / "storage" / "pdfs"))

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

# =========================
# UI (V4.3 Phase 2.2)
# =========================

from .ui import *  # noqa: E402, F403
