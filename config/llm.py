"""
LLM Provider Configuration
===========================
All LLM-related settings are read from environment variables here.
Every provider reads from this single source of truth.
"""

import os

# =========================
# LLM — Unified
# =========================

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_STREAM = os.getenv("LLM_STREAM", "false").lower() == "true"

# =========================
# DeepSeek
# =========================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# =========================
# Gemini
# =========================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")