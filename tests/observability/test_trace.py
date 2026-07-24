import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from observability.models import AgentSpan, AgentTrace
from observability.tracer import (
    add_span,
    finish_trace,
    get_trace_by_id,
    get_trace_by_request_id,
    get_trace_detail,
    get_traces,
    node_span,
    start_trace,
)
from storage.database import Base

TEST_DATABASE_URL = "sqlite:///./test_observability.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _setup_db():
    import billing.models  # noqa: F401
    import observability.models  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_observability.db"):
        try:
            os.remove("test_observability.db")
        except (PermissionError, OSError):
            pass


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _persist(db_session, trace):
    return finish_trace(trace, db=db_session)


class TestTraceLifecycle:
    def test_start_trace_creates_agent_trace(self):
        trace = start_trace(
            thread_id="test-thread",
            tenant_id=1,
            user_id=1,
        )
        assert trace.request_id is not None
        assert trace.tenant_id == 1
        assert trace.thread_id == "test-thread"
        assert trace.status == "started"
        assert trace.started_at is not None

    def test_start_trace_unique_request_ids(self):
        trace1 = start_trace(thread_id="t1", tenant_id=1)
        trace2 = start_trace(thread_id="t2", tenant_id=1)
        assert trace1.request_id != trace2.request_id

    def test_finish_trace_saves_to_db(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(
            trace,
            status="success",
            metadata={"quality_score": 90.0, "tools_used": ["search"]},
            db=db_session,
        )
        assert saved.status == "success"
        assert saved.finished_at is not None
        assert saved.duration_ms is not None
        assert saved.meta["quality_score"] == 90.0

    def test_finish_trace_failed_status(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(
            trace,
            status="failed",
            metadata={"error": "timeout"},
            db=db_session,
        )
        assert saved.status == "failed"

    def test_finish_trace_cache_hit(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(
            trace,
            status="cache_hit",
            metadata={"cache": True},
            db=db_session,
        )
        assert saved.status == "cache_hit"

    def test_finish_trace_fallback(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(
            trace,
            status="fallback",
            metadata={"reason": "agent_unavailable"},
            db=db_session,
        )
        assert saved.status == "fallback"


class TestAgentSpan:
    def test_add_span(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(trace, status="success", db=db_session)

        span = add_span(
            trace=saved,
            node_name="planner",
            status="success",
            duration_ms=100.0,
            metadata={"plan": ["step1", "step2"]},
        )
        assert span.node_name == "planner"
        assert span.status == "success"
        assert span.duration_ms == 100.0
        assert span.meta["plan"] == ["step1", "step2"]

    def test_node_span_context_manager(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(trace, status="success", db=db_session)

        with node_span(saved, "retriever", metadata={"docs": 5}):
            pass

        assert saved is not None

    def test_node_span_handles_error(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(trace, status="success", db=db_session)

        with pytest.raises(ValueError):
            with node_span(saved, "tool", metadata={"tool": "search"}):
                raise ValueError("test error")


class TestTraceQueries:
    def test_get_trace_by_request_id(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(trace, status="success", db=db_session)

        found = get_trace_by_request_id(db_session, saved.request_id)
        assert found is not None
        assert found.id == saved.id

    def test_get_trace_by_id(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(trace, status="success", db=db_session)

        found = get_trace_by_id(db_session, saved.id)
        assert found is not None
        assert found.request_id == saved.request_id

    def test_get_trace_detail(self, db_session):
        trace = start_trace(thread_id="test", tenant_id=1)
        saved = finish_trace(trace, status="success", db=db_session)

        detail = get_trace_detail(db_session, saved.id)
        assert detail is not None
        assert detail["request_id"] == saved.request_id
        assert detail["status"] == "success"
        assert "spans" in detail

    def test_get_trace_detail_not_found(self, db_session):
        detail = get_trace_detail(db_session, 99999)
        assert detail is None

    def test_get_traces_tenant_filtered(self, db_session):
        trace1 = start_trace(thread_id="t1", tenant_id=1)
        finish_trace(trace1, status="success", db=db_session)

        trace2 = start_trace(thread_id="t2", tenant_id=2)
        finish_trace(trace2, status="success", db=db_session)

        traces = get_traces(db_session, tenant_id=1)
        assert len(traces) == 1
        assert traces[0]["thread_id"] == "t1"

    def test_get_traces_with_limit(self, db_session):
        for i in range(5):
            trace = start_trace(thread_id=f"t{i}", tenant_id=1)
            finish_trace(trace, status="success", db=db_session)

        traces = get_traces(db_session, tenant_id=1, limit=3)
        assert len(traces) == 3


class TestTenantIsolation:
    def test_traces_not_visible_across_tenants(self, db_session):
        trace1 = start_trace(thread_id="t1", tenant_id=1)
        finish_trace(trace1, status="success", db=db_session)

        trace2 = start_trace(thread_id="t2", tenant_id=2)
        finish_trace(trace2, status="success", db=db_session)

        t1_traces = get_traces(db_session, tenant_id=1)
        t2_traces = get_traces(db_session, tenant_id=2)

        assert len(t1_traces) == 1
        assert len(t2_traces) == 1
        assert t1_traces[0]["thread_id"] == "t1"
        assert t2_traces[0]["thread_id"] == "t2"