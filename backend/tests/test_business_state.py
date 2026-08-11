"""
Unit tests for app.schemas.business_state — pure Pydantic validation,
no database needed.
"""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.workflow import WorkflowStatus
from app.schemas.business_state import (
    ApprovalData,
    ApprovalStatus,
    BusinessState,
    EmailData,
    KnowledgeData,
    PersonalizationData,
    ResearchData,
    SessionInfo,
    WorkflowInput,
)


def _minimal_state(**overrides) -> BusinessState:
    defaults = dict(
        session=SessionInfo(
            workflow_id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        ),
        input=WorkflowInput(
            company_name="Acme Corp",
            recipient_email="contact@acme.com",
            purpose="Partnership outreach",
        ),
    )
    defaults.update(overrides)
    return BusinessState(**defaults)


# --- 1. Minimal valid BusinessState -----------------------------------


def test_minimal_business_state_constructs():
    state = _minimal_state()

    assert state.session.workflow_id is not None
    assert state.input.company_name == "Acme Corp"


# --- 2. Optional/default values ----------------------------------------


def test_default_values_are_correct():
    state = _minimal_state()

    assert state.input.additional_notes is None

    assert state.research.industry is None
    assert state.research.website is None
    assert state.research.products == []
    assert state.research.recent_news == []
    assert state.research.business_summary is None
    assert state.research.research_completed is False

    assert state.knowledge.retrieved_chunks == []
    assert state.knowledge.source_document_ids == []

    assert state.personalization.draft_email_subject is None
    assert state.personalization.draft_email_body is None

    assert state.approval.approval_status == ApprovalStatus.PENDING
    assert state.approval.approved_email_subject is None
    assert state.approval.approved_email_body is None
    assert state.approval.approval_notes is None

    assert state.email.email_sent is False
    assert state.email.email_message_id is None
    assert state.email.email_sent_at is None

    assert state.status == WorkflowStatus.PENDING
    assert state.error_message is None


# --- 3. Fully populated BusinessState -----------------------------------


def test_fully_populated_business_state_validates():
    state = _minimal_state(
        input=WorkflowInput(
            company_name="Acme Corp",
            recipient_email="contact@acme.com",
            purpose="Partnership outreach",
            additional_notes="Met at a conference last month.",
        ),
        research=ResearchData(
            industry="Software",
            website="https://acme.example.com",
            products=["Widget Pro", "Widget Lite"],
            recent_news=["Acme raises Series B"],
            business_summary="Acme builds developer tooling.",
            research_completed=True,
        ),
        knowledge=KnowledgeData(
            retrieved_chunks=["Our SOP for outreach is ..."],
            source_document_ids=[uuid.uuid4()],
        ),
        personalization=PersonalizationData(
            draft_email_subject="Let's partner up",
            draft_email_body="Hi there, ...",
        ),
        approval=ApprovalData(
            approval_status=ApprovalStatus.APPROVED,
            approved_email_subject="Let's partner up",
            approved_email_body="Hi there, ... (approved)",
            approval_notes="Looks good, ship it.",
        ),
        email=EmailData(
            email_sent=True,
            email_message_id="msg-12345",
            email_sent_at=datetime.now(timezone.utc),
        ),
        status=WorkflowStatus.COMPLETED,
    )

    assert state.research.research_completed is True
    assert state.approval.approval_status == ApprovalStatus.APPROVED
    assert state.email.email_sent is True
    assert state.status == WorkflowStatus.COMPLETED


# --- 4. Invalid recipient EmailStr ---------------------------------------


def test_invalid_recipient_email_raises():
    with pytest.raises(ValidationError):
        WorkflowInput(
            company_name="Acme Corp",
            recipient_email="not-an-email",
            purpose="Partnership outreach",
        )


# --- 5. Invalid WorkflowStatus enum value --------------------------------


def test_invalid_workflow_status_raises():
    with pytest.raises(ValidationError):
        _minimal_state(status="not_a_real_status")


def test_invalid_approval_status_raises():
    with pytest.raises(ValidationError):
        ApprovalData(approval_status="not_a_real_status")


# --- 6. JSON serialization -----------------------------------------------


def test_business_state_is_json_serializable():
    state = _minimal_state()

    json_str = state.model_dump_json()

    assert isinstance(json_str, str)
    assert "pending" in json_str  # WorkflowStatus.PENDING serialized as its value

    # Round-trips back into an equivalent object.
    rehydrated = BusinessState.model_validate_json(json_str)
    assert rehydrated.input.company_name == state.input.company_name
    assert rehydrated.status == state.status


def test_fully_populated_business_state_is_json_serializable():
    state = _minimal_state(
        email=EmailData(
            email_sent=True,
            email_message_id="msg-1",
            email_sent_at=datetime.now(timezone.utc),
        ),
    )

    json_str = state.model_dump_json()
    rehydrated = BusinessState.model_validate_json(json_str)

    assert rehydrated.email.email_sent is True
    assert rehydrated.email.email_sent_at is not None


# --- 7. List defaults are independent between instances -------------------


def test_mutable_list_defaults_are_independent_between_instances():
    state_a = _minimal_state()
    state_b = _minimal_state()

    state_a.research.products.append("Product X")
    state_a.knowledge.retrieved_chunks.append("some chunk")

    assert state_a.research.products == ["Product X"]
    assert state_b.research.products == []  # untouched

    assert state_a.knowledge.retrieved_chunks == ["some chunk"]
    assert state_b.knowledge.retrieved_chunks == []  # untouched