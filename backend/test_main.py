from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool
import pytest
from src.main import app
from src.database import get_session
from src.organizations.models import Organization, UserOrganizationLink
from src.users.models import User
import uuid

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def get_token(client: TestClient, email, password):
    client.post("/users/", json={"email": email, "password": password})
    response = client.post("/auth/login", data={"username": email, "password": password})
    return response.json()["access_token"]

def test_organization_crud(client: TestClient, session: Session):
    # 1. Setup - Create two users
    token_owner = get_token(client, "owner@example.com", "pass")
    token_stranger = get_token(client, "stranger@example.com", "pass")
    
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_stranger = {"Authorization": f"Bearer {token_stranger}"}

    # 2. Create Org
    response = client.post(
        "/organizations/",
        json={"name": "Owner Corp", "description": "Original"},
        headers=headers_owner
    )
    assert response.status_code == 200
    org_id = response.json()["id"]

    # 3. Read
    response = client.get(f"/organizations/{org_id}", headers=headers_owner)
    assert response.status_code == 200
    assert response.json()["name"] == "Owner Corp"

    # 4. Update - Unauthorized (Stranger tries to update)
    response = client.put(
        f"/organizations/{org_id}",
        json={"name": "Heist Corp"},
        headers=headers_stranger
    )
    assert response.status_code == 403

    # 5. Update - Authorized (Owner updates)
    response = client.put(
        f"/organizations/{org_id}",
        json={"name": "Mega Corp"},
        headers=headers_owner
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Mega Corp"

    # 6. Delete - Unauthorized
    response = client.delete(f"/organizations/{org_id}", headers=headers_stranger)
    assert response.status_code == 403

    # 7. Delete - Authorized
    response = client.delete(f"/organizations/{org_id}", headers=headers_owner)
    assert response.status_code == 200

    # 8. Verify Delete
    response = client.get(f"/organizations/{org_id}", headers=headers_owner)
    assert response.status_code == 404
