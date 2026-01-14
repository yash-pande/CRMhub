from sqlmodel import SQLModel, create_engine, Session
from src.config import settings

# -- Educational Note --
# Now we read the URL from our settings. This is "12-Factor App" compliant.
# If we deploy to AWS, we just set the DATABASE_URL env var, and no code changes needed.

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
