from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
import uuid

from src.database import get_session
from src.organizations.schemas import (
    OrganizationCreate, 
    OrganizationRead, 
    OrganizationUpdate,
    InviteCreate,
    InviteResponse,
    JoinRequest,
    MemberRoleUpdate,
    MemberRead
)
from src.organizations import service
from src.auth.router import get_current_user
from src.users.models import User
from src.organizations.models import UserOrganizationLink, OrgRole

router = APIRouter(prefix="/organizations", tags=["organizations"])

@router.post("/", response_model=OrganizationRead)
def create_organization(
    org_create: OrganizationCreate, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return service.create_organization(session, org_create, current_user.id)
# ]
@router.get("/",response_model=List[OrganizationRead])
def read_organizations(
    offset: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return service.get_all_organizations(session, offset, limit)


@router.get("/{org_id}",response_model=OrganizationRead)
def read_organization(
    org_id: uuid.UUID, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    org = service.get_organization(session, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org 

@router.put("/{org_id}", response_model=OrganizationRead)
def update_organization(
    org_id: uuid.UUID, 
    org_update: OrganizationUpdate, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Authorization Check: Is user an owner/admin?
    link = session.exec(
        select(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == current_user.id)
        .where(UserOrganizationLink.organization_id == org_id)
    ).first()
    
    # We check against the Enum values
    if not link or link.role not in [OrgRole.OWNER, OrgRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions"
        )
        
    org = service.get_organization(session, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    return service.update_organization(session, org, org_update)

@router.delete("/{org_id}")
def delete_organization(
    org_id: uuid.UUID, 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Authorization Check: Only owner can delete
    link = session.exec(
        select(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == current_user.id)
        .where(UserOrganizationLink.organization_id == org_id)
    ).first()
    
    if not link or link.role != OrgRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only owners can delete organizations"
        )
        
    org = service.get_organization(session, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    service.delete_organization(session, org)
    return {"ok": True}

@router.post("/{org_id}/invite", response_model=InviteResponse)
def create_invitation(
    org_id: uuid.UUID,
    invite: InviteCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Authorization Check
    link = session.exec(
        select(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == current_user.id)
        .where(UserOrganizationLink.organization_id == org_id)
    ).first()
    
    if not link or link.role not in [OrgRole.OWNER, OrgRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions to invite users"
        )
        
    token = service.create_invitation_token(org_id, invite.expiration_minutes)
    
    # Construct a link. In a real app, this base URL should be in settings.
    # We'll assume the frontend handles the joining at /join?token=...
    # or the API is used directly. I'll provide a generic API link format.
    invitation_url = f"/organizations/join?token={token}" 
    
    return InviteResponse(invitation_url=invitation_url, token=token)

@router.post("/join")
def join_organization(
    join_request: JoinRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    org_id = service.verify_invitation_token(join_request.token)
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token"
        )
        
    # Check if user is already a member
    existing_link = session.exec(
        select(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == current_user.id)
        .where(UserOrganizationLink.organization_id == org_id)
    ).first()
    
    if existing_link:
        return {"message": "You are already a member of this organization", "org_id": org_id}
        
    service.add_member(session, org_id, current_user.id, OrgRole.MEMBER)
    return {"message": "Successfully joined organization", "org_id": org_id}

@router.delete("/{org_id}/members/{user_id}")
def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Check requester permissions
    requester_link = service.get_member_link(session, org_id, current_user.id)
    if not requester_link or requester_link.role not in [OrgRole.OWNER, OrgRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 2. Check target member
    target_link = service.get_member_link(session, org_id, user_id)
    if not target_link:
        raise HTTPException(status_code=404, detail="Member not found in this organization")

    # 3. Hierarchy check
    if requester_link.role == OrgRole.ADMIN:
        if target_link.role in [OrgRole.OWNER, OrgRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Admins cannot remove other Admins or Owners")
            
    if target_link.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot remove the Owner")

    service.remove_member(session, org_id, user_id)
    return {"ok": True}

@router.put("/{org_id}/members/{user_id}", response_model=MemberRoleUpdate)
def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role_update: MemberRoleUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # 1. Check requester permissions
    requester_link = service.get_member_link(session, org_id, current_user.id)
    if not requester_link or requester_link.role not in [OrgRole.OWNER, OrgRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    # 2. Check target member
    target_link = service.get_member_link(session, org_id, user_id)
    if not target_link:
        raise HTTPException(status_code=404, detail="Member not found")
        
    # 3. Hierarchy check
    if requester_link.role == OrgRole.ADMIN:
        if target_link.role in [OrgRole.OWNER, OrgRole.ADMIN]:
            raise HTTPException(status_code=403, detail="Admins cannot modify other Admins or Owners")
        if role_update.role in [OrgRole.OWNER, OrgRole.ADMIN]:
             raise HTTPException(status_code=403, detail="Admins cannot promote to Admin/Owner")
             
    if target_link.role == OrgRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot change role of the Owner")
        
    updated_link = service.update_member_role(session, org_id, user_id, role_update.role)
    return role_update

@router.get("/{org_id}/members", response_model=List[MemberRead])
def read_members(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Authorization: Any member can see other members? 
    # Usually yes. We should check if the user is a member of this org.
    link = service.get_member_link(session, org_id, current_user.id)
    if not link:
        # If not a member, verify if it's consistent with Read Organization
        # But for privacy, usually only members/admins can see member list.
        # We'll stick to members-only for now.
        raise HTTPException(status_code=403, detail="Not a member of this organization")
        
    return service.get_members(session, org_id)