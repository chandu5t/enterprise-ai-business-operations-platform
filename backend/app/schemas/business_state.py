"""
BusinessState — the typed runtime state passed through every LangGraph
node (Module 5) and populated by every agent (Modules 6-10).

This module defines the shape of that state only. It contains no graph
wiring, no node logic, and no agent behavior — those belong to their
own modules. BusinessState exists now so later modules have a single,
well-typed object to read from and write to instead of passing raw
prompts between agents, per the project's TDD.

Reuses WorkflowStatus from app.models.workflow rather than defining a
second status enum — one status vocabulary, shared by the DB column
and the runtime state, so the two can never drift apart.
"""

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.workflow import WorkflowStatus


class SessionInfo(BaseModel):
    """Identifies which workflow/organization/user this state belongs to."""

    workflow_id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID


class WorkflowInput(BaseModel):
    """The original inputs the workflow was started with — mirrors the
    fields already on app.models.workflow.Workflow."""

    company_name: str
    recipient_email: EmailStr
    purpose: str
    additional_notes: str | None = None


class ResearchData(BaseModel):
    """Research Agent output (populated in Module 6). All fields are
    optional/default-empty since this section is unpopulated until the
    Research node actually runs."""

    industry: str | None = None
    website: str | None = None
    products: list[str] = Field(default_factory=list)
    recent_news: list[str] = Field(default_factory=list)
    business_summary: str | None = None
    research_completed: bool = False


class KnowledgeData(BaseModel):
    """RAG retrieval output (populated in Module 7)."""

    retrieved_chunks: list[str] = Field(default_factory=list)
    source_document_ids: list[uuid.UUID] = Field(default_factory=list)


class PersonalizationData(BaseModel):
    """Personalization Agent's drafted email, before human review
    (populated in Module 8)."""

    draft_email_subject: str | None = None
    draft_email_body: str | None = None


class ApprovalStatus(str, enum.Enum):
    """
    Outcome of the human-in-the-loop review (Module 9).

    Deliberately separate from WorkflowStatus: this tracks the
    approval decision itself, not the workflow's overall lifecycle
    stage (WorkflowStatus.AWAITING_APPROVAL is what tracks that a
    workflow is currently at this stage). Colocated here rather than
    in app.models, the same way UserRole lives next to User and
    DocumentType lives next to Document — this enum has no SQLAlchemy
    column yet (Approvals table/persistence is Module 9's concern).
    """

    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class ApprovalData(BaseModel):
    """Human-in-the-loop approval outcome (populated in Module 9)."""

    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_email_subject: str | None = None
    approved_email_body: str | None = None
    approval_notes: str | None = None


class EmailData(BaseModel):
    """Email Agent send result (populated in Module 10)."""

    email_sent: bool = False
    email_message_id: str | None = None
    email_sent_at: datetime | None = None


class BusinessState(BaseModel):
    """
    The single object every LangGraph node (Module 5) and agent
    (Modules 6-10) reads from and writes to. Organized into nested
    sections — one per concern — mirroring the TDD's own state design,
    so each future agent's docstring can say precisely which section it
    reads and which it writes.
    """

    session: SessionInfo
    input: WorkflowInput
    research: ResearchData = Field(default_factory=ResearchData)
    knowledge: KnowledgeData = Field(default_factory=KnowledgeData)
    personalization: PersonalizationData = Field(
        default_factory=PersonalizationData
    )
    approval: ApprovalData = Field(default_factory=ApprovalData)
    email: EmailData = Field(default_factory=EmailData)

    status: WorkflowStatus = WorkflowStatus.PENDING
    error_message: str | None = None