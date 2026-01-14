from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
import uuid
from datetime import datetime, timezone

# We need to import the Link model for 'link_model' to work without strings (which were failing)
# We use a postponed import or handle circularity carefully.
# However, importing 'src.organizations.models' here is safe because that file
# only imports 'src.users.models' inside TYPE_CHECKING blocks.
from src.organizations.models import UserOrganizationLink, Organization

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    
    # User Request: Name is filled later
    name: Optional[str] = None
    
    pfp: Optional[str] = None
    is_active: bool = Field(default=True)

    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    organizations: List[Organization] = Relationship(back_populates="users", link_model=UserOrganizationLink)
