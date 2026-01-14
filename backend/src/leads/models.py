from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
import uuid
from datetime import datetime, timezone
from enum import Enum

if TYPE_CHECKING:
    from src.users.models import User
    from src.organizations.models import Organization

class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    WON = "won"

class Lead(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    email: Optional[str] = None
    phone: Optional[str] = None
    status: LeadStatus = Field(default=LeadStatus.NEW)
    source: Optional[str] = None
    notes: Optional[str] = None
    
    organization_id: uuid.UUID = Field(foreign_key="organization.id")
    assigned_to_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    organization: "Organization" = Relationship()
    assigned_to: Optional["User"] = Relationship()
