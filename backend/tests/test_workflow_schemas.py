"""
Tests for app.schemas.workflow — WorkflowCreate (pure validation) and
WorkflowResponse/WorkflowSummary (validated from a real Workflow ORM
instance via from_attributes=True, using the existing db_session
fixture — same pattern as tests/test_database.py).
"""

import pytest
from pydantic import ValidationError

from app.models.organization import Organization
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStatus
from app.schemas.workflow import WorkflowCreate, WorkflowResponse, WorkflowSummary


# --- 1. Valid WorkflowCreate -----------------------------------------------


def test_workflow_create_accepts_valid_payload():
    workflow_in = WorkflowCreate(
        company_name="Acme Corp",
        recipient_email="contact@acme.com",
        purpose="Partnership outreach",
        additional_notes="Met at a conference.",
    )

    assert workflow_in.company_name == "Acme Corp"
    assert workflow_in.additional_notes == "Met at a conference."


def test_workflow_create_additional_notes_defaults_to_none():
    workflow_in = WorkflowCreate(
        company_name="Acme Corp",
        recipient_email="contact@acme.com",
        purpose="Partnership outreach",
    )

    assert workflow_in.additional_notes is None


# --- 2. Invalid WorkflowCreate -----------------------------------------------


def test_workflow_create_rejects_invalid_email():
    with pytest.raises(ValidationError):
        WorkflowCreate(
            company_name="Acme Corp",
            recipient_email="not-an-email",
            purpose="Partnership outreach",
        )


def test_workflow_create_rejects_missing_required_field():
    with pytest.raises(ValidationError):
        WorkflowCreate(
            recipient_email="contact@acme.com",
            purpose="Partnership outreach",
        )  # missing company_name


# --- 3 & 4. WorkflowResponse validation, directly from an ORM instance -------


def _create_workflow(db_session, **overrides) -> Workflow:
    org = Organization(name=overrides.pop("organization_name", "Umbrella LLC"))
    user = User(
        organization=org,
        email=overrides.pop("user_email", "bob@umbrella.com"),
        hashed_password="hash",
        full_name="Bob Example",
    )
    db_session.add_all([org, user])
    db_session.flush()

    defaults = dict(
        organization_id=org.id,
        created_by=user.id,
        company_name="Target Co",
        recipient_email="contact@targetco.com",
        purpose="Partnership outreach",
    )
    defaults.update(overrides)

    workflow = Workflow(**defaults)
    db_session.add(workflow)
    db_session.flush()
    db_session.refresh(workflow)
    return workflow


def test_workflow_response_validates_from_orm_instance(db_session):
    workflow = _create_workflow(db_session)

    response = WorkflowResponse.model_validate(workflow)

    assert response.id == workflow.id
    assert response.organization_id == workflow.organization_id
    assert response.created_by == workflow.created_by
    assert response.company_name == "Target Co"
    assert response.recipient_email == "contact@targetco.com"
    assert response.purpose == "Partnership outreach"
    assert response.additional_notes is None
    assert response.status == WorkflowStatus.PENDING
    assert response.created_at is not None
    assert response.updated_at is not None


def test_workflow_response_reflects_non_default_status(db_session):
    workflow = _create_workflow(db_session, status=WorkflowStatus.COMPLETED)

    response = WorkflowResponse.model_validate(workflow)

    assert response.status == WorkflowStatus.COMPLETED


# --- 5. WorkflowSummary validation ------------------------------------------


def test_workflow_summary_validates_from_orm_instance(db_session):
    workflow = _create_workflow(db_session)

    summary = WorkflowSummary.model_validate(workflow)

    assert summary.id == workflow.id
    assert summary.company_name == "Target Co"
    assert summary.status == WorkflowStatus.PENDING
    assert summary.created_at is not None


# --- 6. Response schemas expose only their intended fields -------------------


def test_workflow_response_exposes_exactly_the_intended_fields():
    expected = {
        "id",
        "organization_id",
        "created_by",
        "company_name",
        "recipient_email",
        "purpose",
        "additional_notes",
        "status",
        "created_at",
        "updated_at",
    }
    assert set(WorkflowResponse.model_fields.keys()) == expected


def test_workflow_summary_exposes_exactly_the_intended_fields():
    expected = {"id", "company_name", "status", "created_at"}
    assert set(WorkflowSummary.model_fields.keys()) == expected


def test_workflow_summary_excludes_recipient_email_and_notes(db_session):
    # WorkflowSummary is the lightweight list-view — it must not carry
    # recipient_email or additional_notes even though the ORM object has them.
    workflow = _create_workflow(db_session)

    summary = WorkflowSummary.model_validate(workflow)

    assert "recipient_email" not in summary.model_fields
    assert "additional_notes" not in summary.model_fields