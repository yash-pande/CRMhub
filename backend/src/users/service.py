from typing import Optional, List
from sqlmodel import Session, select
from passlib.context import CryptContext
import bcrypt
from src.users.models import User
from src.users.schemas import UserCreate, UserUpdate
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_user(session: Session, user_create: UserCreate) -> User:
    hashed_password = get_password_hash(user_create.password)
    user_data = user_create.model_dump(exclude={"password"})
    db_user = User(**user_data, hashed_password=hashed_password)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def get_user(session: Session, user_id: uuid.UUID) -> Optional[User]:
    return session.get(User, user_id)

def get_all_users(session: Session, offset: int = 0, limit: int = 100) -> List[User]:
    return session.exec(select(User).offset(offset).limit(limit)).all()

def update_user(session: Session, db_user: User, user_update: UserUpdate) -> User:
    update_data = user_update.model_dump(exclude_unset=True)
    
    # If password is being updated, hash it
    if "password" in update_data and update_data["password"]:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

def delete_user(session: Session, db_user: User) -> None:
    session.delete(db_user)
    session.commit()
