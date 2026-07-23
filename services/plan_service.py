import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.plan import Plan
from models.subscription import TenantSubscription
from models.usage import UsageRecord
from core.usage_events import UsageEvent
from storage.database import SessionLocal

logger = logging.getLogger(__name__)

DEFAULT_PLAN_SLUG = "free"


def _get_default_plan(db: Session) -> Optional[Plan]:
    return db.query(Plan).filter(Plan.slug == DEFAULT_PLAN_SLUG).first()


def _get_tenant_plan(db: Session, tenant_id: int) -> Plan:
    sub = (
        db.query(TenantSubscription)
        .filter(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active",
        )
        .first()
    )
    if sub and sub.plan:
        return sub.plan
    default = _get_default_plan(db)
    if default:
        return default
    return Plan(
        name="Fallback",
        slug="fallback",
        max_documents=10,
        max_chats_per_day=50,
        max_embeddings=1000,
    )


def get_tenant_subscription(db: Session, tenant_id: int) -> Optional[dict]:
    sub = (
        db.query(TenantSubscription)
        .filter(
            TenantSubscription.tenant_id == tenant_id,
            TenantSubscription.status == "active",
        )
        .first()
    )
    if sub is None:
        return None
    return {
        "id": sub.id,
        "tenant_id": sub.tenant_id,
        "plan": {
            "id": sub.plan.id,
            "name": sub.plan.name,
            "slug": sub.plan.slug,
            "max_documents": sub.plan.max_documents,
            "max_chats_per_day": sub.plan.max_chats_per_day,
            "max_embeddings": sub.plan.max_embeddings,
        },
        "status": sub.status,
        "start_date": sub.start_date.isoformat() if sub.start_date else None,
        "end_date": sub.end_date.isoformat() if sub.end_date else None,
    }


def can_upload(db: Session, tenant_id: int) -> bool:
    return check_plan_limit(db, tenant_id, UsageEvent.DOCUMENT_UPLOAD, "documents")


def can_chat(db: Session, tenant_id: int) -> bool:
    return check_plan_limit(db, tenant_id, UsageEvent.CHAT_REQUEST, "chats")


def check_plan_limit(
    db: Session,
    tenant_id: int,
    event_type: str,
    limit_type: str,
) -> bool:
    plan = _get_tenant_plan(db, tenant_id)

    if limit_type == "documents":
        limit = plan.max_documents
        count = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.event_type == event_type,
            )
            .count()
        )
        return count < limit

    if limit_type == "chats":
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        limit = plan.max_chats_per_day
        count = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.event_type == event_type,
                UsageRecord.created_at >= today_start,
            )
            .count()
        )
        return count < limit

    if limit_type == "embeddings":
        limit = plan.max_embeddings
        count = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.event_type == event_type,
            )
            .count()
        )
        return count < limit

    return True


def initialize_default_plans(db: Session) -> None:
    existing = db.query(Plan).filter(Plan.slug == DEFAULT_PLAN_SLUG).first()
    if existing is None:
        free_plan = Plan(
            name="Free",
            slug="free",
            max_documents=10,
            max_chats_per_day=50,
            max_embeddings=1000,
            price=0.0,
        )
        db.add(free_plan)

    existing_pro = db.query(Plan).filter(Plan.slug == "pro").first()
    if existing_pro is None:
        pro_plan = Plan(
            name="Pro",
            slug="pro",
            max_documents=100,
            max_chats_per_day=500,
            max_embeddings=10000,
            price=29.99,
        )
        db.add(pro_plan)

    existing_ent = db.query(Plan).filter(Plan.slug == "enterprise").first()
    if existing_ent is None:
        ent_plan = Plan(
            name="Enterprise",
            slug="enterprise",
            max_documents=1000,
            max_chats_per_day=5000,
            max_embeddings=100000,
            price=99.99,
        )
        db.add(ent_plan)

    db.commit()
    logger.info("Default plans initialized")