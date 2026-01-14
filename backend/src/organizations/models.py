from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
import uuid
from datetime import datetime, timezone
from enum import Enum

if TYPE_CHECKING:
    from src.users.models import User

class OrgRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    OWNER = "owner"
    VIEWER = "viewer"

class UserOrganizationLink(SQLModel, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", primary_key=True)
    organization_id: uuid.UUID = Field(foreign_key="organization.id", primary_key=True)
    role: OrgRole = Field(default=OrgRole.MEMBER) 
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Organization(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationship back to Users
    users: List["User"] = Relationship(back_populates="organizations", link_model=UserOrganizationLink)
