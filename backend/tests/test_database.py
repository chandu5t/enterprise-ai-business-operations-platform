"""
Tests for the database layer: engine connectivity, ORM model creation,
relationships, and constraint enforcement against a real PostgreSQL
database.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import Document, DocumentType, Organization, User, UserRole, Workflow, WorkflowStatus


def test_engine_connects(db_engine):
    """The engine can actually open a connection and run a query."""
    with db_engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_create_organization(db_session):
    org = Organization(name="Acme Corp")
    db_session.add(org)
    db_session.flush()

    assert org.id is not None
    assert org.created_at is not None
    assert org.updated_at is not None


def test_create_user_linked_to_organization(db_session):
    org = Organization(name="Globex Inc")
    db_session.add(org)
    db_session.flush()

    user = User(
        organization_id=org.id,
        email="alice@globex.com",
        hashed_password="not-a-real-hash",
        full_name="Alice Example",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.flush()

    assert user.id is not None
    assert user.role == UserRole.ADMIN
    assert user.is_active is True  # column default applied
    assert user.organization.name == "Globex Inc"
    assert user in org.users


def test_duplicate_email_raises_integrity_error(db_session):
    org = Organization(name="Initech")
    db_session.add(org)
    db_session.flush()

    db_session.add(
        User(
            organization_id=org.id,
            email="dupe@initech.com",
            hashed_password="hash1",
            full_name="First User",
        )
    )
    db_session.flush()

    db_session.add(
        User(
            organization_id=org.id,
            email="dupe@initech.com",
            hashed_password="hash2",
            full_name="Second User",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_create_workflow_with_default_status(db_session):
    org = Organization(name="Umbrella LLC")
    user = User(
        organization=org,
        email="bob@umbrella.com",
        hashed_password="hash",
        full_name="Bob Example",
    )
    db_session.add_all([org, user])
    db_session.flush()

    workflow = Workflow(
        organization_id=org.id,
        created_by=user.id,
        company_name="Target Co",
        recipient_email="contact@targetco.com",
        purpose="Partnership outreach",
    )
    db_session.add(workflow)
    db_session.flush()

    assert workflow.status == WorkflowStatus.PENDING
    assert workflow.created_by_user.email == "bob@umbrella.com"
    assert workflow.organization.name == "Umbrella LLC"


def test_create_document_and_cascade_delete(db_session):
    org = Organization(name="Soylent Corp")
    user = User(
        organization=org,
        email="carol@soylent.com",
        hashed_password="hash",
        full_name="Carol Example",
    )
    db_session.add_all([org, user])
    db_session.flush()

    document = Document(
        organization_id=org.id,
        uploaded_by=user.id,
        filename="company-sop.pdf",
        file_type=DocumentType.PDF,
        storage_path="/storage/org/soylent/company-sop.pdf",
    )
    db_session.add(document)
    db_session.flush()

    assert document.is_indexed is False  # column default applied
    assert document.uploaded_by_user.full_name == "Carol Example"

    # Deleting the organization must cascade to its documents (ondelete="CASCADE").
    db_session.delete(org)
    db_session.flush()

    remaining = db_session.get(Document, document.id)
    assert remaining is None