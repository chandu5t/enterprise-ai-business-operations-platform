"""Workflow model and status enum — one row per business-automation run."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class WorkflowStatus(str, enum.Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    RETRIEVING_KNOWLEDGE = "retrieving_knowledge"
    PERSONALIZING = "personalizing"
    AWAITING_APPROVAL = "awaiting_approval"
    SENDING_EMAIL = "sending_email"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class Workflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflows"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status"),
        nullable=False,
        default=WorkflowStatus.PENDING,
    )

    organization: Mapped["Organization"] = relationship(back_populates="workflows")
    created_by_user: Mapped["User"] = relationship(back_populates="workflows")

    def __repr__(self) -> str:
        return f"<Workflow id={self.id} company={self.company_name!r} status={self.status.value}>"