from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
import uuid

from src.database import get_session
from src.users.schemas import UserCreate, UserRead, UserUpdate
from src.users import service
from src.users.models import User

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserRead)
def register_user(user_create: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.email == user_create.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return service.create_user(session, user_create)

@router.get("/", response_model=List[UserRead])
def read_users(offset: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    return service.get_all_users(session, offset, limit)

@router.get("/{user_id}", response_model=UserRead)
def read_user(user_id: uuid.UUID, session: Session = Depends(get_session)):
    user = service.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, user_update: UserUpdate, session: Session = Depends(get_session)):
    user = service.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return service.update_user(session, user, user_update)

@router.delete("/{user_id}")
def delete_user(user_id: uuid.UUID, session: Session = Depends(get_session)):
    user = service.get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    service.delete_user(session, user)
    return {"ok": True}
