from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import Optional

from src.organizations.models import OrgRole

class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationRead(OrganizationBase):
    id: uuid.UUID
    created_at: datetime

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class InviteCreate(BaseModel):
    expiration_minutes: int = 10080  # 7 days default

class InviteResponse(BaseModel):
    invitation_url: str
    token: str

class JoinRequest(BaseModel):
    token: str

class MemberRoleUpdate(BaseModel):
    role: OrgRole

class MemberRead(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    pfp: Optional[str] = None
    role: OrgRole
    joined_at: datetime
