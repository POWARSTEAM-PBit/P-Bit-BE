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

import uuid

def test_remove_student_from_class_success(client, teacher_payload, class_payload):
    """
    Integration test for removing a student from a class by the class teacher.
    - Registers and logs in a teacher.
    - Creates a class.
    - An anonymous student joins the class.
    - Teacher removes the student.
    """

    # Step 1: Register and login teacher
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
    class_id = class_data["id"]
    passphrase = class_data["passphrase"]

    # Step 3: Anonymous student joins the class (use unique name)
    unique_name = f"Anon{uuid.uuid4().hex[:6]}"
    anon_payload = {
        "first_name": unique_name,
        "passphrase": passphrase,
        "pin_code": "9999"
    }
    join_resp = client.post("/class/join-anonymous", json=anon_payload)
    assert join_resp.status_code == 200, join_resp.json()

    anon_data = join_resp.json()["data"]
    student_id = anon_data["student_id"]

    # Step 4: Teacher removes the student from the class
    remove_url = f"/class/{class_id}/remove-student/{student_id}"
    remove_resp = client.delete(remove_url, headers=teacher_headers)
    assert remove_resp.status_code == 200, remove_resp.json()

    remove_data = remove_resp.json()["data"]
    assert remove_data["student_id"] == student_id
    assert remove_data["class_id"] == class_id
    assert remove_data["first_name"] == unique_name


def test_get_owned_classes(client, teacher_payload, class_payload):
    """
    Integration test for retrieving classes owned by a teacher.
    - Registers and logs in a teacher.
    - Creates one or more classes.
    - Retrieves owned classes via /class/owned endpoint.
    
    Verifies that the teacher receives their created classes with accurate details and member count.
    """

    # Step 1: Register and log in teacher
    reg_resp = client.post("/user/register", json=teacher_payload)
    assert reg_resp.status_code == 201

    login_resp = client.post("/user/login", data={
        "username": teacher_payload["user_id"],
        "password": teacher_payload["password"]
    })
    assert login_resp.status_code == 200
    teacher_token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {teacher_token}"}

    # Step 2: Create one or more classes
    num_classes = 2
    created_classes = []

    for i in range(num_classes):
        new_class_payload = {
            **class_payload,
            "name": f"{class_payload['name']}_{uuid.uuid4().hex[:6]}"
        }
        create_resp = client.post("/class/create", json=new_class_payload, headers=headers)
        assert create_resp.status_code == 201
        created_classes.append(create_resp.json()["data"])

    # Step 3: Retrieve owned classes
    owned_resp = client.get("/class/owned", headers=headers)
    assert owned_resp.status_code == 200

    owned_data = owned_resp.json()["data"]
    assert isinstance(owned_data, list)
    assert len(owned_data) >= num_classes

    # Step 4: Validate each created class is present with correct data
    owned_ids = {c["id"] for c in owned_data}
    for created in created_classes:
        assert created["id"] in owned_ids

    for c in owned_data:
        assert "id" in c
        assert "name" in c
        assert "subject" in c
        assert "description" in c
        assert "passphrase" in c
        assert "owner_id" in c
        assert "owner_name" in c
        assert "member_count" in c
        assert isinstance(c["member_count"], int)

def test_get_enrolled_classes(client, teacher_payload, student_payload, class_payload):
    """
    Integration test for retrieving classes where a student is enrolled.
    
    - A teacher creates a class.
    - A student registers and joins that class using the passphrase.
    - The student fetches their enrolled classes.
    
    Verifies successful class joining and correct data returned by /class/enrolled.
    """

    # Step 1: Register and log in as teacher
    reg_teacher = client.post("/user/register", json=teacher_payload)
    assert reg_teacher.status_code == 201

    login_teacher = client.post("/user/login", data={
        "username": teacher_payload["user_id"],
        "password": teacher_payload["password"]
    })
    assert login_teacher.status_code == 200
    teacher_token = login_teacher.json()["data"]["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    # Step 2: Create a class
    unique_class = {
        **class_payload,
        "name": f"{class_payload['name']}_{uuid.uuid4().hex[:5]}"
    }
    create_resp = client.post("/class/create", json=unique_class, headers=teacher_headers)
    assert create_resp.status_code == 201
    created_class = create_resp.json()["data"]
    passphrase = created_class["passphrase"]

    # Step 3: Register and log in as student
    reg_student = client.post("/user/register", json=student_payload)
    assert reg_student.status_code == 201

    login_student = client.post("/user/login", data={
        "username": student_payload["user_id"],
        "password": student_payload["password"]
    })
    assert login_student.status_code == 200
    student_token = login_student.json()["data"]["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Step 4: Join class as student
    join_payload = {"passphrase": passphrase}
    join_resp = client.post("/class/join", json=join_payload, headers=student_headers)
    assert join_resp.status_code == 200

    # Step 5: Get enrolled classes
    enrolled_resp = client.get("/class/enrolled", headers=student_headers)
    assert enrolled_resp.status_code == 200

    data = enrolled_resp.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1

    # Step 6: Validate the structure and content of enrolled class data
    found = False
    for cls in data:
        assert "id" in cls
        assert "name" in cls
        assert "subject" in cls
        assert "description" in cls
        assert "owner_id" in cls
        assert "owner_name" in cls
        assert "member_count" in cls
        assert "joined_at" in cls
        assert "created_at" in cls

        if cls["id"] == created_class["id"]:
            found = True
            assert cls["name"] == unique_class["name"]
            assert cls["subject"] == class_payload["subject"]
            assert cls["description"] == class_payload["description"]

    assert found, "Created class not found in enrolled list"


def test_delete_class_by_owner(client, teacher_payload, class_payload):
    """
    Integration test for deleting a class by its owner (teacher).
    
    - Registers and logs in a teacher.
    - Creates a class.
    - Deletes the created class.
    
    Verifies successful deletion and proper status codes.
    """
    # Step 1: Register and log in teacher
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
    unique_class = {
        **class_payload,
        "name": f"{class_payload['name']}_{uuid.uuid4().hex[:6]}"
    }
    create_resp = client.post("/class/create", json=unique_class, headers=teacher_headers)
    assert create_resp.status_code == 201

    class_id = create_resp.json()["data"]["id"]

    # Step 3: Delete class
    delete_resp = client.delete(f"/class/{class_id}", headers=teacher_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True
    assert delete_resp.json()["message"] == "Class deleted successfully"

    # Step 4: Try to fetch deleted class (simulate internal behavior)
    # This assumes a route like `/class/{class_id}` exists (not shown in your code)
    # If it doesn't, you may remove this check or verify indirectly
    # For example:
    delete_again_resp = client.delete(f"/class/{class_id}", headers=teacher_headers)
    assert delete_again_resp.status_code == 404


def test_leave_class_as_student(client, teacher_payload, student_payload, class_payload):
    """
    Integration test where:
    - A teacher creates a class.
    - A student joins the class.
    - The student then leaves the class successfully.
    """

    # 1. Register and login teacher
    client.post("/user/register", json=teacher_payload)
    login_teacher = client.post("/user/login", data={
        "username": teacher_payload["user_id"],
        "password": teacher_payload["password"]
    })
    teacher_token = login_teacher.json()["data"]["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    # 2. Create class
    class_payload["name"] += f"_{uuid.uuid4().hex[:6]}"
    create_resp = client.post("/class/create", json=class_payload, headers=teacher_headers)
    class_id = create_resp.json()["data"]["id"]
    passphrase = create_resp.json()["data"]["passphrase"]

    # 3. Register and login student
    client.post("/user/register", json=student_payload)
    login_student = client.post("/user/login", data={
        "username": student_payload["user_id"],
        "password": student_payload["password"]
    })
    student_token = login_student.json()["data"]["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 4. Student joins the class
    join_resp = client.post("/class/join", json={"passphrase": passphrase}, headers=student_headers)
    assert join_resp.status_code == 200

    # 5. Student leaves the class
    leave_resp = client.delete(f"/class/{class_id}/leave", headers=student_headers)
    assert leave_resp.status_code == 200
    assert leave_resp.json()["success"] is True
    assert leave_resp.json()["message"] == "Successfully left the class"
