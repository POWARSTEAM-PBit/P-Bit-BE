import pytest
from db.db_models import teacher, student
from routes.user import hash_password, user_login

@pytest.fixture
def test_teacher(db):
    """
    Create a test teacher user in the database.
    """
    user = teacher(
        email="teacher@example.com",
        first_name="teacher",
        last_name="teacher",
        password=hash_password("strongpassword123")
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # <--- ADD THIS to ensure you get the updated DB record
    return user

@pytest.fixture
def test_student(db):
    """
    Create a test student user in the database.
    """
    user = student(
        user_name="student1",
        first_name="student",
        last_name = "student",
        password=hash_password("studentpass")
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # <--- ADD THIS to ensure you get the updated DB record
    return user

def test_teacher_login_invalid_email(client):
    """
    Test teacher login with invalid email format.
    """
    login_data = {
        "user_id": "not-an-email",
        "password": "any",
        "user_type": "teacher"
    }
    response = client.post("/user/login", json=login_data)
    assert response.status_code == 400
    assert "Invalid email address" in response.json()["msg"]

def test_student_login_success(client, test_student):
    """
    Test successful login of a student with correct credentials.
    """
    login_data = {
        "user_id": test_student.user_name,
        "password": "studentpass",
        "user_type": "student"
    }
    response = client.post("/user/login", json=login_data)
    assert response.status_code == 200
    assert "message" in response.json()

def test_student_login_wrong_password(client, test_student):
    """
    Test student login fails with wrong password.
    """
    login_data = {
        "user_id": test_student.user_name,
        "password": "incorrect",
        "user_type": "student"
    }
    response = client.post("/user/login", json=login_data)
    assert response.status_code == 401
    assert response.json()["msg"] == "User does not exist"

def test_login_invalid_user_type(client):
    """
    Test login with an invalid user_type returns error.
    """
    login_data = {
        "user_id": "someuser",
        "password": "somepass",
        "user_type": "admin"  # invalid type
    }
    response = client.post("/user/login", json=login_data)
    assert response.status_code == 422
    ##assert response.json()["msg"] == "Invalid user type"
