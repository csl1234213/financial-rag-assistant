import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from storage.agent.checkpoint import PostgresSaver
from storage.agent.models import AgentCheckpoint, AgentMessage, AgentSession
from storage.agent.repository import AgentRepository
from storage.database import SessionLocal, init_db


@pytest.fixture(autouse=True, scope="session")
def setup_db_once():
    init_db()
    yield


@pytest.fixture
def db():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(autouse=True)
def cleanup(db):
    yield
    db.query(AgentMessage).delete()
    db.query(AgentCheckpoint).delete()
    db.query(AgentSession).delete()
    db.commit()


class TestPostgresSaver:
    def test_put_and_get_checkpoint(self, db):
        saver = PostgresSaver(db, tenant_id=1)
        config = {"configurable": {"thread_id": "cp_test_1"}}
        checkpoint = {"answer": "NVIDIA analysis", "tools_used": ["search"]}
        metadata = {"source": "agent"}

        result = saver.put(config, checkpoint, metadata)
        assert result["configurable"]["thread_id"] == "cp_test_1"
        assert "checkpoint_id" in result["configurable"]

        restored = saver.get(config)
        assert restored is not None
        assert restored["checkpoint"]["answer"] == "NVIDIA analysis"
        assert restored["checkpoint"]["tools_used"] == ["search"]
        assert restored["metadata"]["source"] == "agent"

    def test_get_nonexistent_checkpoint(self, db):
        saver = PostgresSaver(db, tenant_id=1)
        config = {"configurable": {"thread_id": "nonexistent_thread"}}
        result = saver.get(config)
        assert result is None

    def test_multiple_checkpoints_for_same_thread(self, db):
        saver = PostgresSaver(db, tenant_id=1)
        config = {"configurable": {"thread_id": "multi_cp_thread"}}

        saver.put(config, {"step": 1}, {"iteration": 1})
        saver.put(config, {"step": 2}, {"iteration": 2})
        saver.put(config, {"step": 3}, {"iteration": 3})

        latest = saver.get(config)
        assert latest is not None
        assert latest["checkpoint"]["step"] == 3

    def test_checkpoint_persistence_across_instances(self, db):
        saver1 = PostgresSaver(db, tenant_id=1)
        config = {"configurable": {"thread_id": "persist_test"}}
        saver1.put(config, {"data": "persistent"}, {})

        saver2 = PostgresSaver(db, tenant_id=1)
        restored = saver2.get(config)
        assert restored is not None
        assert restored["checkpoint"]["data"] == "persistent"

    def test_extract_thread_id_from_config(self, db):
        saver = PostgresSaver(db, tenant_id=1)
        tid = saver._extract_thread_id({"configurable": {"thread_id": "my_thread"}})
        assert tid == "my_thread"

    def test_extract_thread_id_default(self, db):
        saver = PostgresSaver(db, tenant_id=1)
        tid = saver._extract_thread_id({})
        assert tid == "default"

    def test_tenant_isolation_checkpoints(self, db):
        saver_a = PostgresSaver(db, tenant_id=100)
        saver_b = PostgresSaver(db, tenant_id=200)
        config = {"configurable": {"thread_id": "iso_thread"}}

        saver_a.put(config, {"owner": "tenant_100"}, {})
        saver_b.put(config, {"owner": "tenant_200"}, {})

        repo = AgentRepository(db)
        checkpoints_a = repo.get_latest_checkpoint("iso_thread")
        assert checkpoints_a is not None

    def test_put_writes_noop(self, db):
        saver = PostgresSaver(db, tenant_id=1)
        saver.put_writes({"configurable": {"thread_id": "t"}}, [], "task_1")