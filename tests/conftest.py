import gc
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_TEST_RUN_ROOT = Path(
    tempfile.mkdtemp(prefix="financial-rag-pytest-")
).resolve()
os.environ["FINANCIAL_RAG_TEST_RUN_ROOT"] = str(_TEST_RUN_ROOT)
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = (
    f"sqlite:///{(_TEST_RUN_ROOT / 'application.db').as_posix()}"
)
os.environ["CHROMA_PATH"] = str(_TEST_RUN_ROOT / "chroma")
os.environ["CACHE_DIR"] = str(_TEST_RUN_ROOT / "cache")
os.environ["UPLOAD_DIR"] = str(_TEST_RUN_ROOT / "uploads")
os.environ["PDF_DIR"] = str(_TEST_RUN_ROOT / "pdfs")
os.environ.pop("CHROMA_HOST", None)

import pytest
from fastapi.testclient import TestClient

from tests.storage_paths import dispose_sqlite_test_engines


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
    from api.app import app

    with TestClient(app) as test_client:
        yield test_client


def pytest_sessionfinish(session, exitstatus):
    """Close process-wide stores before removing this run's isolated state."""

    del session, exitstatus

    database_module = sys.modules.get("storage.database")
    if database_module is not None:
        database_module.engine.dispose(close=True)

    core_engine_module = sys.modules.get("core.core_engine")
    core_store = (
        getattr(core_engine_module, "_store", None)
        if core_engine_module is not None
        else None
    )
    close_core_store = getattr(core_store, "close", None)
    if callable(close_core_store):
        close_core_store()

    dispose_sqlite_test_engines()
    gc.collect()

    for attempt in range(5):
        try:
            shutil.rmtree(_TEST_RUN_ROOT)
            break
        except FileNotFoundError:
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(0.1 * (attempt + 1))
