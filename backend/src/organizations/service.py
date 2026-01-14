from typing import Optional, List
from sqlmodel import Session, select
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uuid
from src.config import settings
from src.organizations.models import Organization, UserOrganizationLink, OrgRole
from src.organizations.schemas import OrganizationCreate, OrganizationUpdate
from src.users.models import User

def create_organization(session: Session, org_create: OrganizationCreate, owner_id: uuid.UUID) -> Organization:
    # 1. Create Org
    db_org = Organization.model_validate(org_create)
    session.add(db_org)
    session.commit()
    session.refresh(db_org)

    # 2. Add Creator as Owner
    link = UserOrganizationLink(
        user_id=owner_id,
        organization_id=db_org.id,
        role=OrgRole.OWNER
    )
    session.add(link)
    session.commit()
    
    return db_org

def get_organization(session: Session, org_id: uuid.UUID) -> Optional[Organization]:
    return session.get(Organization, org_id)

def get_all_organizations(session: Session, offset: int = 0, limit: int = 100) -> List[Organization]:
    return session.exec(select(Organization).offset(offset).limit(limit)).all()

def update_organization(session: Session, db_org: Organization, org_update: OrganizationUpdate) -> Organization:
    update_data = org_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)
    session.add(db_org)
    session.commit()
    session.refresh(db_org)
    return db_org

def delete_organization(session: Session, db_org: Organization) -> None:
    session.delete(db_org)
    session.commit()

def add_member(session: Session, org_id: uuid.UUID, user_id: uuid.UUID, role: OrgRole = OrgRole.MEMBER) -> UserOrganizationLink:
    link = UserOrganizationLink(
        user_id=user_id,
        organization_id=org_id,
        role=role
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link

def create_invitation_token(org_id: uuid.UUID, expiration_minutes: int = 10080) -> str:
    """Generate a JWT token for invitation."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expiration_minutes)
    to_encode = {
        "sub": "invitation", 
        "org_id": str(org_id),
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_invitation_token(token: str) -> Optional[uuid.UUID]:
    """Decode token to get org_id. Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("sub") != "invitation":
            return None
        org_id_str = payload.get("org_id")
        if not org_id_str:
            return None
        return uuid.UUID(org_id_str)
    except (JWTError, ValueError):
        return None

def get_member_link(session: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> Optional[UserOrganizationLink]:
    return session.exec(
        select(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == user_id)
        .where(UserOrganizationLink.organization_id == org_id)
    ).first()

def remove_member(session: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    link = get_member_link(session, org_id, user_id)
    if link:
        session.delete(link)
        session.commit()
        return True
    return False

def update_member_role(session: Session, org_id: uuid.UUID, user_id: uuid.UUID, role: OrgRole) -> Optional[UserOrganizationLink]:
    link = get_member_link(session, org_id, user_id)
    if link:
        link.role = role
        session.add(link)
        session.commit()
        session.refresh(link)
        return link
    return None

def get_members(session: Session, org_id: uuid.UUID) -> List[dict]:
    """Get all members of an organization with their details."""
    results = session.exec(
        select(UserOrganizationLink, User)
        .where(UserOrganizationLink.organization_id == org_id)
        .join(User, UserOrganizationLink.user_id == User.id)
    ).all()
    
    members = []
    for link, user in results:
        members.append({
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "pfp": user.pfp,
            "role": link.role,
            "joined_at": link.joined_at
        })
    return members
