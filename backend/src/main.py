from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.database import create_db_and_tables
from src.config import settings
from src.users.router import router as users_router
from src.organizations.router import router as orgs_router
from src.auth.router import router as auth_router
from src.leads.router import router as leads_router
from src.leads.history_models import LeadHistory  # Import to ensure table creation

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(orgs_router)
app.include_router(leads_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the CRM API"}
