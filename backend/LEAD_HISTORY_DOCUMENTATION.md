# Lead History Feature - Implementation Details

## Overview

The Lead History feature provides complete audit trail tracking for all actions performed on leads in the CRM system. Every time a lead is created, updated, assigned, or has its status changed, a history record is automatically created with before/after snapshots.

---

## New Files Created

### 1. `src/leads/history_models.py`

This file contains the database model for tracking lead history.

#### LeadAction Enum
```python
class LeadAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    DELETED = "deleted"
```

**Purpose**: Categorizes the type of action performed on a lead.

#### LeadHistory Model
```python
class LeadHistory(SQLModel, table=True):
    id: uuid.UUID                    # Unique ID for this history entry
    lead_id: uuid.UUID               # Links to the lead
    action: LeadAction               # Type of action performed
    performed_by_id: uuid.UUID       # User who performed the action
    description: str                 # Human-readable description
    old_value: Optional[dict]        # Complete lead state BEFORE change (JSON)
    new_value: Optional[dict]        # Complete lead state AFTER change (JSON)
    created_at: datetime             # When this action occurred
```

**Key Features**:
- **old_value** and **new_value** store complete snapshots of the lead as JSON
- This allows you to see exactly what changed and potentially restore previous states
- Automatic timestamps track when each action occurred
- References to both the lead and the user who made the change

---

## Changes to Existing Files

### 2. `src/leads/service.py`

Added two new helper functions and modified existing CRUD functions:

#### New Function: `create_lead_history()`
```python
def create_lead_history(
    session: Session,
    lead_id: uuid.UUID,
    action: str,
    performed_by_id: uuid.UUID,
    description: str,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None
)
```

**Purpose**: Helper function to create history entries. Called automatically by create/update operations.

**Parameters**:
- `action`: What happened (created, updated, assigned, etc.)
- `performed_by_id`: User who performed the action
- `description`: Human-readable description like "Lead updated: status: new → contacted"
- `old_value`: Lead state before the change
- `new_value`: Lead state after the change

#### New Function: `get_lead_history()`
```python
def get_lead_history(session: Session, lead_id: uuid.UUID, org_id: uuid.UUID)
```

**Purpose**: Retrieve all history entries for a specific lead.

**Security**: First verifies the lead belongs to the specified organization before returning history.

**Returns**: List of history entries ordered by most recent first.

#### Modified: `create_lead()`
**Change**: Now accepts `user_id` parameter

**Addition**: After creating the lead, automatically creates a history entry:
```python
create_lead_history(
    session=session,
    lead_id=db_lead.id,
    action="created",
    performed_by_id=user_id,
    description=f"Lead '{db_lead.name}' was created",
    new_value=db_lead.model_dump()  # Stores complete lead state
)
```

**Why**: Tracks who created each lead and when, with full initial state.

#### Modified: `update_lead()`
**Changes**: 
1. Now accepts `user_id` parameter
2. Stores the old state before making changes
3. Tracks which fields actually changed
4. Creates appropriate history entry based on what changed

**Smart Action Detection**:
```python
if "assigned_to_id" in update_data:
    action = "assigned"
elif "status" in update_data:
    action = "status_changed"  
else:
    action = "updated"
```

**Change Tracking**:
```python
for key, value in update_data.items():
    old_value = getattr(db_lead, key)
    if old_value != value:
        setattr(db_lead, key, value)
        changes.append(f"{key}: {old_value} → {value}")
```

This creates descriptions like: `"Lead updated: status: new → contacted, assigned_to_id: None → uuid123"`

---

### 3. `src/leads/router.py`

#### Modified: `create_lead()` endpoint
**Change**: Now passes `current_user.id` to the service function.

**Before**:
```python
return service.create_lead(session, lead_create, org_id)
```

**After**:
```python
return service.create_lead(session, lead_create, org_id, current_user.id)
```

**Why**: Need to track which user created the lead.

#### Modified: `update_lead()` endpoint
**Change**: Now passes `current_user.id` to the service function.

**Before**:
```python
return service.update_lead(session, lead, lead_update)
```

**After**:
```python
return service.update_lead(session, lead, lead_update, current_user.id)
```

**Why**: Need to track which user updated the lead.

#### New Endpoint: `get_lead_history()`
```python
@router.get("/{lead_id}/history")
def get_lead_history(
    org_id: uuid.UUID,
    lead_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
)
```

**URL**: `GET /organizations/{org_id}/leads/{lead_id}/history`

**Purpose**: Retrieve complete history of actions performed on a specific lead.

**Authorization**: Requires user to be a member of the organization (checked by `get_org_link`).

**Returns**: List of history entries with all details.

---

## How It Works: Full Flow

### Creating a Lead

1. **User sends**: `POST /organizations/{org_id}/leads`
   ```json
   {
     "name": "John Doe",
     "email": "john@example.com",
     "status": "new"
   }
   ```

2. **Router** (`create_lead`):
   - Validates user is a member
   - Checks if user is a Viewer (rejects)
   - Validates assigned_to_id if provided
   - Calls `service.create_lead()` with `current_user.id`

3. **Service** (`create_lead`):
   - Creates the lead in database
   - Calls `create_lead_history()` with:
     - action: "created"
     - description: "Lead 'John Doe' was created"
     - new_value: Full lead object as JSON

4. **Result**: 
   - Lead is created
   - History entry is created automatically
   - Both are saved in the database

### Updating a Lead

1. **User sends**: `PATCH /organizations/{org_id}/leads/{lead_id}`
   ```json
   {
     "status": "contacted",
     "notes": "Called and interested"
   }
   ```

2. **Service** (`update_lead`):
   - Stores old state: `old_state = db_lead.model_dump()`
   - Applies changes
   - Tracks what changed: `["status: new → contacted", "notes: None → Called and interested"]`
   - Determines action type: "status_changed" (because status was updated)
   - Creates history with both old and new complete states

3. **Result**:
   - Lead is updated
   - History shows exactly what changed
   - Old state is preserved in history

### Viewing History

1. **User sends**: `GET /organizations/{org_id}/leads/{lead_id}/history`

2. **Service** (`get_lead_history`):
   - Verifies lead exists and belongs to organization
   - Fetches all history entries
   - Orders by newest first

3. **Returns**:
   ```json
   [
     {
       "id": "...",
       "lead_id": "...",
       "action": "status_changed",
       "performed_by_id": "user-uuid",
       "description": "Lead updated: status: new → contacted, notes: None → Called",
       "old_value": {"id": "...", "name": "John Doe", "status": "new", ...},
       "new_value": {"id": "...", "name": "John Doe", "status": "contacted", ...},
       "created_at": "2026-01-14T18:00:00Z"
     },
     {
       "id": "...",
       "lead_id": "...",
       "action": "created",
       "performed_by_id": "user-uuid",
       "description": "Lead 'John Doe' was created",
       "old_value": null,
       "new_value": {"id": "...", "name": "John Doe", "status": "new", ...},
       "created_at": "2026-01-14T17:00:00Z"
     }
   ]
   ```

---

## Database Schema

### New Table: `leadhistory`

```sql
CREATE TABLE leadhistory (
    id UUID PRIMARY KEY,
    lead_id UUID REFERENCES lead(id),
    action VARCHAR (leadaction enum),
    performed_by_id UUID REFERENCES user(id),
    description TEXT,
    old_value JSON,          -- Stores complete lead snapshot
    new_value JSON,          -- Stores complete lead snapshot
    created_at TIMESTAMP
);
```

**Indexes**:
- `lead_id` - for fast lookup of all history for a lead
- Foreign keys ensure referential integrity

---

## Use Cases

### 1. Audit Trail
Track who did what and when:
```
"User Alice created lead 'John Doe' at 3:00 PM"
"User Bob assigned lead to Charlie at 3:15 PM"
"User Charlie updated status from 'new' to 'contacted' at 3:30 PM"
```

### 2. Restore Previous State
With `old_value` and `new_value`, you can:
- See exactly what a lead looked like at any point in time
- Implement an "undo" feature
- Detect who made unwanted changes

### 3. Analytics
- Track how long leads stay in each status
- See which users are most active
- Identify patterns in lead conversion

### 4. Compliance
- Meet regulatory requirements for data tracking
- Provide evidence of actions for disputes
- Maintain complete audit logs

---

## Future Enhancements

### Potential Additions:

1. **Soft Delete Tracking**: 
   - Add "deleted" action type
   - Store deleted lead data before removal

2. **Restore Functionality**:
   - Endpoint to restore lead to a previous state
   - Use `old_value` to recreate previous version

3. **History Filtering**:
   - Filter by action type
   - Filter by user
   - Filter by date range

4. **Aggregated Views**:
   - Timeline view of lead lifecycle
   - User activity dashboard
   - Change frequency metrics

5. **Notifications**:
   - Alert when leads change status
   - Notify when assigned
   - Send digest of daily changes

---

## Security Considerations

1. **Organization Scoping**: 
   - `get_lead_history()` verifies lead belongs to organization
   - Prevents cross-organization history access

2. **Authentication Required**:
   - All endpoints require valid user authentication
   - Uses `get_current_user` dependency

3. **Member-Only Access**:
   - Only organization members can view history
   - Checked via `get_org_link()`

4. **Immutable History**:
   - History entries are never updated or deleted
   - Provides reliable audit trail

---

## Testing the Feature

### 1. Create a lead:
```bash
POST /organizations/{org_id}/leads
{
  "name": "Test Lead",
  "status": "new"
}
```

### 2. Update the lead:
```bash
PATCH /organizations/{org_id}/leads/{lead_id}
{
  "status": "contacted",
  "notes": "First contact made"
}
```

### 3. View history:
```bash
GET /organizations/{org_id}/leads/{lead_id}/history
```

You should see 2 entries: one for creation, one for the update.

---

## Summary

The Lead History feature provides:
- ✅ Complete audit trail of all lead actions
- ✅ Before/after snapshots of changes
- ✅ User attribution (who did what)
- ✅ Timestamp tracking (when it happened)
- ✅ Human-readable descriptions
- ✅ Organization-scoped security
- ✅ Full JSON snapshots for potential restore

This creates a robust foundation for compliance, analytics, and user accountability in your CRM system.
