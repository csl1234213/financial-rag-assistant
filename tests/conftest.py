import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from api.app import app


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )


@pytest.fixture(autouse=True)
def _ensure_providers_registered():
    from llm.adapters.deepseek_provider import DeepSeekProvider
    from llm.adapters.gemini_provider import GeminiProvider
    from llm.providers.provider_registry import ProviderRegistry

    if not ProviderRegistry.has_provider("deepseek"):
        ProviderRegistry.register("deepseek", DeepSeekProvider)
    if not ProviderRegistry.has_provider("gemini"):
        ProviderRegistry.register("gemini", GeminiProvider)


@pytest.fixture(scope="session")
def client():
    return TestClient(app)