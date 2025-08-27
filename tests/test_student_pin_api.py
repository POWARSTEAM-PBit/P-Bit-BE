import pytest
import uuid

@pytest.fixture
def teacher_payload():
    unique_email = f"unique.user.{uuid.uuid4().hex[:8]}@gmail.com"
    return {
        "user_id": unique_email,
        "first_name": "Unique",
        "last_name": "User",
        "password": "MyCoolPassword##",
        "user_type": "teacher"
    }

@pytest.fixture
def student_payload():
    unique_username = f"uniqueuser{uuid.uuid4().hex[:8]}"
    return {
        "user_id": unique_username,
        "first_name": "Unique",
        "last_name": "User",
        "password": "MyCoolPassword##",
        "user_type": "student"
    }

@pytest.fixture
def class_payload():
    return {
        "name": "unique_class_123",
        "subject": "Science",
        "description": "This is a great class"
    }

def test_join_class(client, teacher_payload, student_payload, class_payload):
    """
    Integration test for the workflow where:
    - A teacher registers, logs in, and creates a class.
    - A student registers, logs in, and joins the created class using the class passphrase.
    
    Verifies successful registration, login, class creation, and class joining.
    """

    reg_resp = client.post("/user/register", json=teacher_payload)
    assert reg_resp.status_code == 201

    login_resp = client.post("/user/login", data={
        "username": teacher_payload["user_id"],
        "password": teacher_payload["password"]
    })
    assert login_resp.status_code == 200
    teacher_token = login_resp.json()["data"]["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    # Create class
    create_resp = client.post("/class/create", json=class_payload, headers=teacher_headers)
    assert create_resp.status_code == 201
    class_data = create_resp.json()["data"]
    passphrase = class_data["passphrase"]
    class_id = class_data["id"]

    # Register and login student
    reg_stud_resp = client.post("/user/register", json=student_payload)
    assert reg_stud_resp.status_code == 201

    login_stud_resp = client.post("/user/login", data={
        "username": student_payload["user_id"],
        "password": student_payload["password"]
    })
    assert login_stud_resp.status_code == 200
    student_token = login_stud_resp.json()["data"]["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Student joins the class with passphrase only (logged-in)
    join_payload = {
        "passphrase": passphrase
    }
    join_resp = client.post("/class/join", json=join_payload, headers=student_headers)
    assert join_resp.status_code == 200



def test_set_pin_without_identification(client):
    """
    Integration test for attempting to set a PIN without student identification.
    This should return a 400 error since the endpoint requires student identification,
    but it is not implemented yet.
    """
    payload = {
        "pin_code": "5678"
    }

    response = client.post("/class/set-pin", json=payload)
    
    assert response.status_code == 400
    resp_json = response.json()
    assert resp_json["success"] is False
    assert "Student identification required" in resp_json["message"]


def test_join_anonymous_class(client, teacher_payload, class_payload):
    """
    Integration test for an anonymous user joining a class using the class passphrase and PIN code.
    - Registers and logs in a teacher to create a class.
    - Simulates an anonymous student joining the class using a first name, PIN code, and class passphrase.
    - Verifies the user is successfully added as a class member.
    """

    # Step 1: Register and login the teacher
    reg_resp = client.post("/user/register", json=teacher_payload)
    assert reg_resp.status_code == 201

    login_resp = client.post("/user/login", data={
        "username": teacher_payload["user_id"],
        "password": teacher_payload["password"]
    })
    assert login_resp.status_code == 200
    teacher_token = login_resp.json()["data"]["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    # Step 2: Create class
    create_resp = client.post("/class/create", json=class_payload, headers=teacher_headers)
    assert create_resp.status_code == 201
    class_data = create_resp.json()["data"]
    passphrase = class_data["passphrase"]

    # Step 3: Join class anonymously
    anon_payload = {
        "passphrase": passphrase,
        "first_name": "TestStudent",
        "pin_code": "1234"
    }

    join_resp = client.post("/class/join-anonymous", json=anon_payload)

    # Step 4: Verify join was successful
    assert join_resp.status_code == 200
    resp_json = join_resp.json()
    assert resp_json["success"] is True
    assert "class_id" in resp_json["data"]
    assert resp_json["data"]["first_name"] == anon_payload["first_name"]




def test_create_class(client, teacher_payload, class_payload) -> None:
    """
    Integration test for creating a class by a teacher.
    - Registers a teacher.
    - Logs the teacher in to get an access token.
    - Creates a class with the teacher's authorization.
    
    Verifies successful registration, login, and class creation with expected class details.
    """
    
    register_resp = client.post("/user/register", json=teacher_payload)
    assert register_resp.status_code == 201

    login_data = {
        "username": teacher_payload["user_id"],
        "password": teacher_payload["password"]
    }
    
    login_resp = client.post("/user/login", data=login_data)
    
    assert login_resp.status_code == 200
    
    access_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    create_resp = client.post("/class/create", json=class_payload, headers=headers)
    assert create_resp.status_code == 201

    data = create_resp.json().get("data")
    assert data is not None
    assert data["name"] == class_payload["name"]
    assert data["subject"] == class_payload["subject"]
    assert data["description"] == class_payload["description"]
    assert "passphrase" in data
    assert "owner_id" in data