import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from billing.models import BillingRecord
from observability.metrics import get_agent_metrics, get_daily_metrics
from observability.models import AgentTrace
from observability.tracer import finish_trace, start_trace
from storage.database import Base

TEST_DATABASE_URL = "sqlite:///./test_obs_metrics.db"

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
    if os.path.exists("test_obs_metrics.db"):
        try:
            os.remove("test_obs_metrics.db")
        except (PermissionError, OSError):
            pass


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestAgentMetrics:
    def test_empty_metrics(self, db_session):
        metrics = get_agent_metrics(db_session, tenant_id=1)
        assert metrics["total_requests"] == 0
        assert metrics["total_success"] == 0
        assert metrics["total_failed"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["avg_latency_ms"] == 0.0

    def test_metrics_with_traces(self, db_session):
        for i in range(5):
            trace = start_trace(thread_id=f"t{i}", tenant_id=1)
            finish_trace(
                trace,
                status="success",
                metadata={"duration_ms": 100.0 * (i + 1)},
                db=db_session,
            )

        for i in range(2):
            trace = start_trace(thread_id=f"f{i}", tenant_id=1)
            finish_trace(
                trace,
                status="failed",
                metadata={"error": "timeout"},
                db=db_session,
            )

        metrics = get_agent_metrics(db_session, tenant_id=1)
        assert metrics["total_requests"] == 7
        assert metrics["total_success"] == 5
        assert metrics["total_failed"] == 2
        success_rate = round(5 / 7 * 100, 2)
        assert metrics["success_rate"] == success_rate
        assert metrics["avg_latency_ms"] >= 0.0

    def test_metrics_tenant_isolation(self, db_session):
        trace1 = start_trace(thread_id="t1", tenant_id=1)
        finish_trace(trace1, status="success", db=db_session)

        trace2 = start_trace(thread_id="t2", tenant_id=2)
        finish_trace(trace2, status="success", db=db_session)

        m1 = get_agent_metrics(db_session, tenant_id=1)
        m2 = get_agent_metrics(db_session, tenant_id=2)

        assert m1["total_requests"] == 1
        assert m2["total_requests"] == 1

    def test_metrics_with_cost(self, db_session):
        trace = start_trace(thread_id="t1", tenant_id=1)
        finish_trace(trace, status="success", db=db_session)

        billing = BillingRecord(
            tenant_id=1,
            resource_type="chat",
            quantity=1,
            unit_price=0.005,
            amount=0.005,
            currency="USD",
        )
        db_session.add(billing)
        db_session.commit()

        metrics = get_agent_metrics(db_session, tenant_id=1)
        assert metrics["total_cost"] == 0.005


class TestDailyMetrics:
    def test_empty_daily(self, db_session):
        daily = get_daily_metrics(db_session, tenant_id=1, days=7)
        assert "daily" in daily
        assert len(daily["daily"]) == 0

    def test_daily_aggregation(self, db_session):
        trace = start_trace(thread_id="t1", tenant_id=1)
        finish_trace(trace, status="success", db=db_session)

        daily = get_daily_metrics(db_session, tenant_id=1, days=7)
        assert len(daily["daily"]) >= 1
        day_data = daily["daily"][0]
        assert "date" in day_data
        assert "requests" in day_data
        assert "success" in day_data
        assert "failed" in day_data
        assert "avg_latency_ms" in day_data