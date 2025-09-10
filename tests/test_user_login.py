import pytest
from db.db_models import User, UserType
from routes.user import hash_password

@pytest.fixture
def test_student(db):
    user = User(
        user_id="student1",
        first_name="student",
        last_name="student",
        password=hash_password("studentpass"),
        user_type=UserType.STUDENT
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_teacher(db):
    user = User(
        user_id="teacher@example.com",
        first_name="teacher",
        last_name="teacher",
        password=hash_password("strongpassword123"),
        user_type=UserType.TEACHER
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def test_teacher_login_invalid_email_format(client):
    response = client.post(
        "/user/login",
        data={
            "username": "not-an-email",
            "password": "any",
        }
    )
    # You may choose to return 400 if user doesn't exist or invalid email format
    assert response.status_code in [400, 404, 422]

def test_student_login_success(client, test_student):
    response = client.post(
        "/user/login",
        data={
            "username": test_student.user_id,
            "password": "studentpass"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]

def test_student_login_wrong_password(client, test_student):
    response = client.post(
        "/user/login",
        data={
            "username": test_student.user_id,
            "password": "wrongpass"
        }
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Incorrect password"

def test_login_user_not_found(client):
    response = client.post(
        "/user/login",
        data={
            "username": "nonexistent_user",
            "password": "password"
        }
    )
    assert response.status_code == 404
    assert response.json()["message"] == "User does not exist"
