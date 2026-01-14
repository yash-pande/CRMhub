from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List, Optional
import uuid

from src.database import get_session
from src.auth.router import get_current_user
from src.users.models import User
from src.leads.schemas import LeadCreate, LeadRead, LeadUpdate
from src.leads.models import LeadStatus
from src.leads import service
from src.organizations.models import UserOrganizationLink, OrgRole

# We might want to pass org_id in the path /organizations/{org_id}/leads
# OR have global /leads endpoint but pass org_id in header or query?
# Usually nested is better for hierarchical permissioning but lets stick to
# /organizations/{org_id}/leads structure for clarity and security context.
# However, the user asked for /leads structure in implementation plan?
# Plan said: GET /leads/ which lists leads for "current user's organization".
# But a user might belong to multiple orgs. 
# So best practice is to require org_id. 
# Let's check the plan again. 
# Plan: "GET /leads/ List all leads for the current user's organization."
# If I use /leads/, I need to know WHICH org. 
# I'll stick to /organizations/{org_id}/leads for explicit context.
# Wait, let's keep it simple. If we want /leads, we can assume the user sends org_uuid in a header 
# or we just require org_id in the path. Path is standard.

router = APIRouter(prefix="/organizations/{org_id}/leads", tags=["leads"])

def get_org_link(session: Session, org_id: uuid.UUID, user_id: uuid.UUID) -> UserOrganizationLink:
    link = session.exec(
        select(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == user_id)
        .where(UserOrganizationLink.organization_id == org_id)
    ).first()
    if not link:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    return link

# 
@router.post("/", response_model=LeadRead)
def create_lead(
    org_id: uuid.UUID,
    lead_create: LeadCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Check permissions (Member can create?) Yes usually.
    link = get_org_link(session, org_id, current_user.id)
    
    # Viewers cannot create leads
    if link.role == OrgRole.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Viewers cannot create leads"
        )
    
    # Validate assigned_to_id if provided
    if lead_create.assigned_to_id:
        # Check if the user exists in this organization
        assigned_user_link = session.exec(
            select(UserOrganizationLink)
            .where(UserOrganizationLink.user_id == lead_create.assigned_to_id)
            .where(UserOrganizationLink.organization_id == org_id)
        ).first()
        
        if not assigned_user_link:
            raise HTTPException(
                status_code=400, 
                detail="Assigned user is not a member of this organization"
            )
    
    return service.create_lead(session, lead_create, org_id, current_user.id)


@router.get("/", response_model=List[LeadRead])
def read_leads(
    org_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    status: Optional[LeadStatus] = Query(None),
    assigned_to_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    get_org_link(session, org_id, current_user.id)
    return service.get_leads(session, org_id, skip, limit, status, assigned_to_id)

@router.get("/{lead_id}", response_model=LeadRead)
def read_lead(
    org_id: uuid.UUID,
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    get_org_link(session, org_id, current_user.id)
    lead = service.get_lead(session, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.patch("/{lead_id}", response_model=LeadRead)
def update_lead(
    org_id: uuid.UUID,
    lead_id: uuid.UUID,
    lead_update: LeadUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    link = get_org_link(session, org_id, current_user.id)
    
    # Viewers cannot update leads
    if link.role == OrgRole.VIEWER:
        raise HTTPException(
            status_code=403,
            detail="Viewers cannot update leads"
        )
    
    lead = service.get_lead(session, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Permission Check for Assignment
    if lead_update.assigned_to_id is not None:
        if lead_update.assigned_to_id != lead.assigned_to_id: # If changing
            if link.role not in [OrgRole.OWNER, OrgRole.ADMIN]:
                raise HTTPException(
                    status_code=403, 
                    detail="Only Owners and Admins can assign leads"
                )

    return service.update_lead(session, lead, lead_update, current_user.id)

@router.delete("/{lead_id}")
def delete_lead(
    org_id: uuid.UUID,
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Only Owner/Admin can delete
    link = get_org_link(session, org_id, current_user.id)
    if link.role not in [OrgRole.OWNER, OrgRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only Owners and Admins can delete leads")
        
    lead = service.get_lead(session, lead_id, org_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    service.delete_lead(session, lead)
    return {"ok": True}

@router.get("/{lead_id}/history")
def get_lead_history(
    org_id: uuid.UUID,
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get history of all actions performed on this lead."""
    link = get_org_link(session, org_id, current_user.id)
    
    history = service.get_lead_history(session, lead_id, org_id)
    return history
