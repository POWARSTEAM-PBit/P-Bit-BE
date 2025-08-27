import pytest
from db.db_models import User, UserType
from routes.user import hash_password

@pytest.fixture
def unique_email():
    return "unique_teacher@example.com"

@pytest.fixture
def unique_username():
    return "unique_student123"

def test_register_teacher_success(client, unique_email):
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

def test_register_student_success(client, unique_username):
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
    payload = {
        "first_name": "Invalid",
        "last_name": "Email",
        "password": "SomePass123!",
        "user_id": "not-an-email",
        "user_type": "teacher"
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert "Invalid email" in data["message"]

def test_register_student_missing_username(client):
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

def test_register_duplicate_teacher(client, db):
    email = "duplicate_teacher@example.com"
    user = User(
        user_id=email,
        first_name="Existing",
        last_name="Teacher",
        password=hash_password("SomePass123!"),
        user_type=UserType.TEACHER
    )
    db.add(user)
    db.commit()

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
    payload = {
        "first_name": "Foo",
        "last_name": "Bar",
        "password": "SomePass123!",
        "user_id": "foo@example.com",
        "user_type": "admin"  # invalid
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 422
