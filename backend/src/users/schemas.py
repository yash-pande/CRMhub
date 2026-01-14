from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
import uuid
from src.organizations.schemas import OrganizationRead

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: uuid.UUID
    name: Optional[str] = None
    pfp: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    organizations: List[OrganizationRead] = []

class UserUpdate(BaseModel):
    name: Optional[str] = None
    pfp: Optional[str] = None
    password: Optional[str] = None


