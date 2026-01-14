from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, JSON
import uuid
from datetime import datetime, timezone
from enum import Enum

if TYPE_CHECKING:
    from src.users.models import User
    from src.leads.models import Lead

class LeadAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    DELETED = "deleted"

class LeadHistory(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    lead_id: uuid.UUID = Field(foreign_key="lead.id", index=True)
    action: LeadAction
    performed_by_id: uuid.UUID = Field(foreign_key="user.id")
    description: str
    
    # Store old and new values as JSON for tracking changes
    old_value: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    new_value: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    lead: "Lead" = Relationship()
    performed_by: "User" = Relationship()
