import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import app
from models.plan import Plan
from models.subscription import TenantSubscription
from models.tenant import Tenant
from models.user import User
from models.usage import UsageRecord
from core.usage_events import UsageEvent, ResourceType
from services.plan_service import (
    can_upload,
    can_chat,
    check_plan_limit,
    get_tenant_subscription,
    initialize_default_plans,
)
from services.usage_service import record_usage
from storage.database import Base, get_db

TEST_DATABASE_URL = "sqlite:///./test_subscription.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DATABASE_URL.replace("sqlite:///", "")):
        try:
            os.remove(TEST_DATABASE_URL.replace("sqlite:///", ""))
        except (PermissionError, OSError):
            pass


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def tenant(db_session):
    t = Tenant(name="Sub Test Co", slug="sub-test")
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


@pytest.fixture
def user(db_session, tenant):
    u = User(
        email="sub@test.com",
        password_hash="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def auth_headers(user):
    from auth.jwt import create_access_token
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestPlanModel:

    def test_create_plan(self, db_session):
        plan = Plan(
            name="Test Plan",
            slug="test-plan",
            max_documents=5,
            max_chats_per_day=10,
            max_embeddings=100,
            price=9.99,
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        assert plan.id is not None
        assert plan.name == "Test Plan"
        assert plan.slug == "test-plan"
        assert plan.max_documents == 5
        assert plan.max_chats_per_day == 10
        assert plan.max_embeddings == 100
        assert plan.price == 9.99
        assert plan.is_active is True

    def test_plan_slug_unique(self, db_session):
        plan1 = Plan(name="Plan A", slug="unique-slug", max_documents=5, max_chats_per_day=10, max_embeddings=100, price=0)
        plan2 = Plan(name="Plan B", slug="unique-slug", max_documents=10, max_chats_per_day=20, max_embeddings=200, price=0)
        db_session.add(plan1)
        db_session.commit()

        db_session.add(plan2)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestTenantSubscriptionModel:

    def test_create_subscription(self, db_session, tenant):
        plan = Plan(
            name="Sub Plan",
            slug="sub-plan",
            max_documents=20,
            max_chats_per_day=100,
            max_embeddings=500,
            price=19.99,
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)

        assert sub.id is not None
        assert sub.tenant_id == tenant.id
        assert sub.plan_id == plan.id
        assert sub.status == "active"
        assert sub.start_date is not None

    def test_subscription_tenant_relationship(self, db_session, tenant):
        plan = Plan(
            name="Rel Plan",
            slug="rel-plan",
            max_documents=10,
            max_chats_per_day=50,
            max_embeddings=200,
            price=0,
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)

        db_session.refresh(tenant)
        assert tenant.subscription is not None
        assert tenant.subscription.id == sub.id
        assert tenant.subscription.plan.name == "Rel Plan"

    def test_subscription_plan_relationship(self, db_session, tenant):
        plan = Plan(
            name="Plan Rel",
            slug="plan-rel",
            max_documents=10,
            max_chats_per_day=50,
            max_embeddings=200,
            price=0,
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()
        db_session.refresh(sub)

        assert sub.plan is not None
        assert sub.plan.id == plan.id
        assert sub.plan.name == "Plan Rel"


class TestPlanService:

    def test_initialize_default_plans(self, db_session):
        initialize_default_plans(db_session)

        free = db_session.query(Plan).filter(Plan.slug == "free").first()
        assert free is not None
        assert free.max_documents == 10
        assert free.max_chats_per_day == 50
        assert free.price == 0.0

        pro = db_session.query(Plan).filter(Plan.slug == "pro").first()
        assert pro is not None
        assert pro.price == 29.99

        ent = db_session.query(Plan).filter(Plan.slug == "enterprise").first()
        assert ent is not None
        assert ent.price == 99.99

    def test_initialize_default_plans_idempotent(self, db_session):
        initialize_default_plans(db_session)
        first_count = db_session.query(Plan).count()
        initialize_default_plans(db_session)
        second_count = db_session.query(Plan).count()
        assert first_count == second_count

    def test_can_upload_within_limit(self, db_session, tenant):
        initialize_default_plans(db_session)
        assert can_upload(db=db_session, tenant_id=tenant.id) is True

    def test_can_upload_at_limit(self, db_session, tenant):
        initialize_default_plans(db_session)
        for _ in range(10):
            record_usage(
                tenant_id=tenant.id,
                event_type=UsageEvent.DOCUMENT_UPLOAD,
                resource_type=ResourceType.DOCUMENT,
                quantity=1,
                db=db_session,
            )
        assert can_upload(db=db_session, tenant_id=tenant.id) is False

    def test_can_chat_within_limit(self, db_session, tenant):
        initialize_default_plans(db_session)
        assert can_chat(db=db_session, tenant_id=tenant.id) is True

    def test_can_chat_at_limit(self, db_session, tenant):
        initialize_default_plans(db_session)
        for _ in range(50):
            record_usage(
                tenant_id=tenant.id,
                event_type=UsageEvent.CHAT_REQUEST,
                resource_type=ResourceType.CHAT,
                quantity=1,
                db=db_session,
            )
        assert can_chat(db=db_session, tenant_id=tenant.id) is False

    def test_custom_plan_limits(self, db_session, tenant):
        plan = Plan(
            name="Custom",
            slug="custom",
            max_documents=3,
            max_chats_per_day=5,
            max_embeddings=50,
            price=0,
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()

        for _ in range(2):
            record_usage(
                tenant_id=tenant.id,
                event_type=UsageEvent.DOCUMENT_UPLOAD,
                resource_type=ResourceType.DOCUMENT,
                quantity=1,
                db=db_session,
            )
        assert can_upload(db=db_session, tenant_id=tenant.id) is True

        record_usage(
            tenant_id=tenant.id,
            event_type=UsageEvent.DOCUMENT_UPLOAD,
            resource_type=ResourceType.DOCUMENT,
            quantity=1,
            db=db_session,
        )
        assert can_upload(db=db_session, tenant_id=tenant.id) is False

    def test_get_tenant_subscription(self, db_session, tenant):
        initialize_default_plans(db_session)
        plan = db_session.query(Plan).filter(Plan.slug == "pro").first()

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()

        result = get_tenant_subscription(db=db_session, tenant_id=tenant.id)
        assert result is not None
        assert result["plan"]["slug"] == "pro"
        assert result["plan"]["max_documents"] == 100
        assert result["status"] == "active"

    def test_get_tenant_subscription_none(self, db_session, tenant):
        result = get_tenant_subscription(db=db_session, tenant_id=tenant.id)
        assert result is None


class TestTenantIsolation:

    def test_tenant_a_usage_does_not_affect_tenant_b_limit(self, db_session, tenant, user):
        initialize_default_plans(db_session)

        tenant_b = Tenant(name="Tenant B", slug="tenant-b")
        db_session.add(tenant_b)
        db_session.commit()
        db_session.refresh(tenant_b)

        for _ in range(10):
            record_usage(
                tenant_id=tenant.id,
                user_id=user.id,
                event_type=UsageEvent.DOCUMENT_UPLOAD,
                resource_type=ResourceType.DOCUMENT,
                quantity=1,
                db=db_session,
            )

        assert can_upload(db=db_session, tenant_id=tenant.id) is False
        assert can_upload(db=db_session, tenant_id=tenant_b.id) is True

    def test_tenant_subscription_isolation(self, db_session, tenant, user):
        initialize_default_plans(db_session)
        pro_plan = db_session.query(Plan).filter(Plan.slug == "pro").first()

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=pro_plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()

        tenant_b = Tenant(name="Tenant B", slug="tenant-b-iso")
        db_session.add(tenant_b)
        db_session.commit()
        db_session.refresh(tenant_b)

        result_a = get_tenant_subscription(db=db_session, tenant_id=tenant.id)
        assert result_a is not None
        assert result_a["plan"]["slug"] == "pro"

        result_b = get_tenant_subscription(db=db_session, tenant_id=tenant_b.id)
        assert result_b is None


class TestSubscriptionAPI:

    def test_get_subscription_authenticated(self, client, tenant, db_session, auth_headers):
        initialize_default_plans(db_session)
        pro_plan = db_session.query(Plan).filter(Plan.slug == "pro").first()

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=pro_plan.id,
            status="active",
        )
        db_session.add(sub)
        db_session.commit()

        response = client.get("/api/v1/subscription/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == tenant.id
        assert data["subscription"] is not None
        assert data["subscription"]["plan"]["slug"] == "pro"

    def test_get_subscription_unauthenticated(self, client):
        response = client.get("/api/v1/subscription/me")
        assert response.status_code == 401

    def test_get_subscription_no_active_subscription(self, client, tenant, db_session, auth_headers):
        initialize_default_plans(db_session)
        response = client.get("/api/v1/subscription/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["subscription"] is None
        assert data["message"] == "No active subscription"


class TestUploadLimitEnforcement:

    def test_upload_within_limit(self, client, tenant, db_session, auth_headers):
        initialize_default_plans(db_session)
        import io
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
            b"trailer<</Size 3/Root 1 0 R>>\n"
            b"%%EOF"
        )
        pdf_file = io.BytesIO(pdf_content)

        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.pdf", pdf_file, "application/pdf")},
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_upload_at_limit_returns_429(self, client, tenant, db_session, auth_headers):
        initialize_default_plans(db_session)
        for _ in range(10):
            record_usage(
                tenant_id=tenant.id,
                event_type=UsageEvent.DOCUMENT_UPLOAD,
                resource_type=ResourceType.DOCUMENT,
                quantity=1,
                db=db_session,
            )

        import io
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
            b"trailer<</Size 3/Root 1 0 R>>\n"
            b"%%EOF"
        )
        pdf_file = io.BytesIO(pdf_content)

        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.pdf", pdf_file, "application/pdf")},
            headers=auth_headers,
        )
        assert response.status_code == 429
        assert "limit" in response.json()["detail"].lower()


class TestChatLimitEnforcement:

    def test_chat_within_limit(self, client, tenant, db_session, auth_headers):
        initialize_default_plans(db_session)
        from unittest.mock import patch
        from api.services.chat_service import ChatService

        mock_response = {
            "report": "Mock",
            "citations": [],
            "reasoning": {},
            "plan": {},
            "execution_time": 0.1,
        }
        with patch.object(ChatService, "chat", return_value=mock_response):
            response = client.post(
                "/api/v1/chat",
                json={"question": "Hello", "company": "TestCorp"},
                headers=auth_headers,
            )
        assert response.status_code == 200

    def test_chat_at_limit_returns_429(self, client, tenant, db_session, auth_headers):
        initialize_default_plans(db_session)
        for _ in range(50):
            record_usage(
                tenant_id=tenant.id,
                event_type=UsageEvent.CHAT_REQUEST,
                resource_type=ResourceType.CHAT,
                quantity=1,
                db=db_session,
            )

        response = client.post(
            "/api/v1/chat",
            json={"question": "Hello", "company": "TestCorp"},
            headers=auth_headers,
        )
        assert response.status_code == 429
        assert "limit" in response.json()["detail"].lower()