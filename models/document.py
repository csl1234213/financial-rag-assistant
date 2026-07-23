from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from storage.database import Base

if TYPE_CHECKING:
    from models.tenant import Tenant


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(128), nullable=False, default="Unknown")
    report_type: Mapped[str] = mapped_column(String(128), nullable=False, default="Financial Report")
    period: Mapped[str] = mapped_column(String(64), nullable=False, default="Unknown")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="indexed")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="documents")
