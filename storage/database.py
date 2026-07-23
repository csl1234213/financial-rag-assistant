import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./financial_rag.db")

_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_default_tenant(db: Session):
    from models.tenant import Tenant

    existing = db.query(Tenant).filter(Tenant.slug == "default").first()
    if existing is None:
        default_tenant = Tenant(name="Default Workspace", slug="default")
        db.add(default_tenant)
        db.commit()


def _ensure_default_plans(db: Session):
    from services.plan_service import initialize_default_plans
    initialize_default_plans(db)


def init_db():
    import models.document  # noqa: F401
    import models.plan  # noqa: F401
    import models.subscription  # noqa: F401
    import models.task  # noqa: F401
    import models.tenant  # noqa: F401
    import models.usage  # noqa: F401
    import models.user  # noqa: F401
    import models.worker_node  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _ensure_default_tenant(db)
        _ensure_default_plans(db)
    finally:
        db.close()