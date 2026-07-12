import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Contact, LinkPrecedence

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the dependency in the app
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    # Create tables before each test
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after each test
    Base.metadata.drop_all(bind=engine)

def test_create_new_primary_contact():
    response = client.post(
        "/identify",
        json={"email": "lorraine@hillvalley.edu", "phoneNumber": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "contact" in data
    
    contact = data["contact"]
    assert contact["primaryContactId"] == 1
    assert contact["emails"] == ["lorraine@hillvalley.edu"]
    assert contact["phoneNumbers"] == ["123456"]
    assert contact["secondaryContactIds"] == []

def test_add_secondary_contact_with_new_info():
    # 1. First purchase (creates primary)
    client.post(
        "/identify",
        json={"email": "mcfly@gmail.com", "phoneNumber": "123456"}
    )
    
    # 2. Second purchase (same email, new phone -> creates secondary)
    response = client.post(
        "/identify",
        json={"email": "mcfly@gmail.com", "phoneNumber": "987654"}
    )
    assert response.status_code == 200
    contact = response.json()["contact"]
    
    assert contact["primaryContactId"] == 1
    assert "mcfly@gmail.com" in contact["emails"]
    assert "123456" in contact["phoneNumbers"]
    assert "987654" in contact["phoneNumbers"]
    assert contact["secondaryContactIds"] == [2]

def test_merge_two_primaries():
    # 1. Doc's first order
    client.post("/identify", json={"email": "doc@gmail.com", "phoneNumber": "1111"})
    
    # 2. Doc's second order (new primary because no overlapping info)
    client.post("/identify", json={"email": "time@gmail.com", "phoneNumber": "2222"})
    
    # 3. Third order links them!
    response = client.post("/identify", json={"email": "doc@gmail.com", "phoneNumber": "2222"})
    
    assert response.status_code == 200
    contact = response.json()["contact"]
    
    # primaryContactId should be the OLDER one (1)
    assert contact["primaryContactId"] == 1
    
    # all info should be consolidated
    assert set(contact["emails"]) == {"doc@gmail.com", "time@gmail.com"}
    assert set(contact["phoneNumbers"]) == {"1111", "2222"}
    
    # The newer primary (2) should now be a secondary
    assert 2 in contact["secondaryContactIds"]
    
def test_no_new_info_no_new_contact():
    # 1. Create primary
    client.post("/identify", json={"email": "biff@tannen.com", "phoneNumber": "5555"})
    
    # 2. Call again with exact same info
    response = client.post("/identify", json={"email": "biff@tannen.com", "phoneNumber": "5555"})
    
    assert response.status_code == 200
    contact = response.json()["contact"]
    
    assert contact["primaryContactId"] == 1
    assert contact["secondaryContactIds"] == [] # Should NOT have created a secondary

def test_validation_error():
    # Must provide at least email or phone
    response = client.post("/identify", json={})
    assert response.status_code == 422 # FastAPI Unprocessable Entity
