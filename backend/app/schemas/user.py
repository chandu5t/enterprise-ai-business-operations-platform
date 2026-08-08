"""Pydantic schemas for User resources — request/response shapes for the API layer."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class UserCreate(UserBase):
    """
    Registration payload.

    organization_name creates a brand-new Organization — it does NOT
    join an existing one. Letting registration join an org by guessing/
    knowing its name would let any registering user gain visibility
    into an unrelated organization's workflows and documents. Multi-user
    organizations are supported via an explicit invite flow in a later
    module, not by name-matching here. Organization.name has a unique
    DB constraint, so a duplicate name is rejected at the service layer
    (see Step 3) with a 409 Conflict.
    """

    password: str = Field(min_length=8, max_length=128)
    organization_name: str = Field(min_length=1, max_length=255)


class UserResponse(UserBase):
    """
    Public-facing user representation.

    Deliberately excludes hashed_password — this is a distinct schema
    from the User ORM model, not the model itself, so that field can
    never leak through the API by accident.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    role: UserRole
    is_active: bool
    created_at: datetime