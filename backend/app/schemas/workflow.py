"""
Pydantic schemas for Workflow request/response shapes.

Mirrors the pattern already established in app/schemas/user.py:
request schemas are plain input contracts, response schemas are a
distinct type from the SQLAlchemy model (never the model itself) with
model_config = ConfigDict(from_attributes=True) so they validate
directly from an ORM instance without leaking internal fields.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.workflow import WorkflowStatus


class WorkflowCreate(BaseModel):
    """Request body for starting a new workflow (wired to an endpoint in
    Module 11 — this schema only defines the input contract)."""

    company_name: str
    recipient_email: EmailStr
    purpose: str
    additional_notes: str | None = None


class WorkflowResponse(BaseModel):
    """
    Full public representation of a Workflow.

    A distinct schema from the Workflow ORM model, not the model
    itself — same reasoning as UserResponse: this is what's safe to
    return over the API, not necessarily every column the table has.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID
    company_name: str
    recipient_email: EmailStr
    purpose: str
    additional_notes: str | None
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime


class WorkflowSummary(BaseModel):
    """Lightweight list-view representation, for a future history/list
    endpoint (Module 11) that shouldn't return every field."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    status: WorkflowStatus
    created_at: datetime