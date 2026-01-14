from typing import Optional, List
from sqlmodel import Session, select
from datetime import datetime, timezone
import uuid

from src.leads.models import Lead, LeadStatus
from src.leads.schemas import LeadCreate, LeadUpdate

def create_lead(session: Session, lead_create: LeadCreate, org_id: uuid.UUID, user_id: uuid.UUID) -> Lead:
    db_lead = Lead(**lead_create.model_dump())
    db_lead.organization_id = org_id
    session.add(db_lead)
    session.commit()
    session.refresh(db_lead)
    
    # Create history entry - only store explicitly set fields
    provided_data = lead_create.model_dump(exclude_unset=True)
    provided_data['organization_id'] = str(org_id)
    
    create_lead_history(
        session=session,
        lead_id=db_lead.id,
        action="created",
        performed_by_id=user_id,
        description=f"Lead '{db_lead.name}' was created",
        new_value=provided_data  # Only fields that were set
    )
    
    return db_lead

def get_leads(
    session: Session, 
    org_id: uuid.UUID, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[LeadStatus] = None,
    assigned_to_id: Optional[uuid.UUID] = None
) -> List[Lead]:
    query = select(Lead).where(Lead.organization_id == org_id)
    
    if status:
        query = query.where(Lead.status == status)
    
    if assigned_to_id:
        query = query.where(Lead.assigned_to_id == assigned_to_id)
        
    return session.exec(query.offset(skip).limit(limit)).all()

def get_lead(session: Session, lead_id: uuid.UUID, org_id: uuid.UUID) -> Optional[Lead]:
    return session.exec(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.organization_id == org_id)
    ).first()

def update_lead(session: Session, db_lead: Lead, lead_update: LeadUpdate, user_id: uuid.UUID) -> Lead:
    update_data = lead_update.model_dump(exclude_unset=True)
    changes = []
    changed_old = {}  # Only store changed fields
    changed_new = {}  # Only store changed fields
    
    for key, value in update_data.items():
        old_value = getattr(db_lead, key)
        if old_value != value:
            setattr(db_lead, key, value)
            changes.append(f"{key}: {old_value} → {value}")
            # Store only the changed field, not entire object
            changed_old[key] = old_value if not isinstance(old_value, uuid.UUID) else str(old_value)
            changed_new[key] = value if not isinstance(value, uuid.UUID) else str(value)
    
    db_lead.updated_at = datetime.now(timezone.utc)
    session.add(db_lead)
    session.commit()
    session.refresh(db_lead)
    
    # Create history entry if there were changes
    if changes:
        action = "assigned" if "assigned_to_id" in update_data else "updated"
        if "status" in update_data:
            action = "status_changed"
            
        create_lead_history(
            session=session,
            lead_id=db_lead.id,
            action=action,
            performed_by_id=user_id,
            description=f"Lead updated: {', '.join(changes)}",
            old_value=changed_old,  # Only changed fields
            new_value=changed_new   # Only changed fields
        )
    
    return db_lead

def delete_lead(session: Session, db_lead: Lead) -> None:
    session.delete(db_lead)
    session.commit()

def create_lead_history(
    session: Session,
    lead_id: uuid.UUID,
    action: str,
    performed_by_id: uuid.UUID,
    description: str,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None
):
    """Helper function to create lead history entry."""
    from src.leads.history_models import LeadHistory, LeadAction
    
    history = LeadHistory(
        lead_id=lead_id,
        action=LeadAction(action),
        performed_by_id=performed_by_id,
        description=description,
        old_value=old_value,
        new_value=new_value
    )
    session.add(history)
    session.commit()
    session.refresh(history)
    return history

def get_lead_history(session: Session, lead_id: uuid.UUID, org_id: uuid.UUID):
    """Get history for a lead (with org check for security)."""
    from src.leads.history_models import LeadHistory
    
    # First verify the lead belongs to this org
    lead = get_lead(session, lead_id, org_id)
    if not lead:
        return []
    
    # Get all history entries
    history = session.exec(
        select(LeadHistory)
        .where(LeadHistory.lead_id == lead_id)
        .order_by(LeadHistory.created_at.desc())
    ).all()
    
    return history