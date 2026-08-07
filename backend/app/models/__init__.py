"""
Import every model here so Base.metadata is fully populated wherever this
package is imported. This is what Alembic's autogenerate relies on to see
the complete schema, and it lets other modules do `from app.models import
User` instead of reaching into individual submodules.
"""

from app.models.document import Document, DocumentType
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.models.workflow import Workflow, WorkflowStatus

__all__ = [
    "Document",
    "DocumentType",
    "Organization",
    "User",
    "UserRole",
    "Workflow",
    "WorkflowStatus",
]