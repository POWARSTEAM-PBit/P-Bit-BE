import pytest
from db.db_models import teacher, student
from routes.user import hash_password

@pytest.fixture
def unique_email():
    return "unique_teacher@example.com"

@pytest.fixture
def unique_username():
    return "unique_student_123"

def test_register_teacher_success(client, db, unique_email):
    """
    Test successful teacher registration with valid input.
    """
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "password": "StrongPassword123!",
        "user_id": unique_email,
        "user_type": "teacher"
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Register successful"

def test_register_student_success(client, db, unique_username):
    """
    Test successful student registration with valid input.
    """
    payload = {
        "first_name": "Jane",
        "last_name": "Smith",
        "password": "SecurePass456!",
        "user_id": unique_username,
        "user_type": "student"
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Register successful"

def test_register_teacher_invalid_email(client):
    """
    Test registration fails when teacher email is invalid.
    """
    payload = {
        "first_name": "Invalid",
        "last_name": "Email",
        "password": "SomePass123!",
        "user_id": "not-an-email",
        "user_type": "teacher"
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "Invalid email address" in data["message"]

def test_register_student_missing_username(client):
    """
    Test student registration fails when username is missing.
    """
    payload = {
        "first_name": "No",
        "last_name": "Username",
        "password": "SomePass123!",
        "user_id": "",
        "user_type": "student"
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "Username is required for student registration" in data["message"]

def test_register_duplicate_teacher(client, db):
    """
    Test duplicate teacher registration fails.
    """
    email = "duplicate_teacher@example.com"
    # Insert manually into DB
    user = teacher(
        email=email,
        first_name="Dupe",
        last_name="User",
        password=hash_password("SomePass123!")
    )
    db.add(user)
    db.commit()

    # Try registering again
    payload = {
        "first_name": "Dupe",
        "last_name": "User",
        "password": "SomePass123!",
        "user_id": email,
        "user_type": "teacher"
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 422
    assert response.json()["message"] == "User already exists"

def test_register_invalid_user_type(client):
    """
    Test register fails for unsupported user type.
    """
    payload = {
        "first_name": "Foo",
        "last_name": "Bar",
        "password": "SomePass123!",
        "user_id": "foo@example.com",
        "user_type": "admin"  # invalid
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 422
    assert response.json()["msg"] == "Invalid user type"
