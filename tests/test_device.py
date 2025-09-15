import pytest
from db.db_models import Device, Class, User
import secrets
import uuid
from passlib.hash import bcrypt
from datetime import datetime

def generate_esp32_mac():
    """
    Generate a 12-character MAC address using hex values,
    similar to the ESP32 Wi-Fi STA interface MAC.
    """
    mac_bytes = [secrets.randbelow(256) for _ in range(6)]
    mac_bytes[0] = (mac_bytes[0] | 0x02) & 0xFE
    mac = ''.join(f'{byte:02x}' for byte in mac_bytes)
    return mac


@pytest.fixture
def test_device(db):
    """
    Fixture to insert a device into the database before a test.
    Used for testing data publishing to a known device.
    """
    mac = generate_esp32_mac()
    device_to_add = Device(mac_addr=mac)

    db.add(device_to_add)
    db.commit()
    db.refresh(device_to_add)
    return device_to_add

@pytest.fixture
def test_class(db):
    """
    Fixture to create a test class and add it to the database.
    """
    class_to_add = Class(
        id=str(uuid.uuid4()),
        name="Test Class",
        subject="Test Subject",
        description="For testing",
        passphrase="testpass123",
        owner_id="test_teacher"
    )
    db.add(class_to_add)
    db.commit()
    db.refresh(class_to_add)
    return class_to_add

@pytest.fixture
def test_teacher(db):
    """
    Fixture to create a teacher user directly in the database.
    """
    unique_email = f"teacher_{uuid.uuid4().hex[:6]}@example.com"
    password = "MyCoolPassword##"

    teacher = User(
        user_id=unique_email,
        first_name="Test",
        last_name="Teacher",
        password=password,
        user_type="teacher",
    )

    return teacher


@pytest.fixture
def test_student(db):
    """
    Fixture to create a student user directly in the database.
    """
    unique_username = f"student_{uuid.uuid4().hex[:6]}"
    password = "MyCoolPassword##"

    student = User(
        user_id=unique_username,
        first_name="Test",
        last_name="Student",
        password=password,
        user_type="student",
    )
    
    return student


def test_device_add(client):
    """
    Test that a new device can be successfully added via /device/add/manf.
    """
    mac = generate_esp32_mac()

    response = client.post(
        "/device/add/manf",
        json={
            "mac_addr": mac
        }
    )

    assert response.status_code == 201


def test_device_data_publish(client, test_device):
    """
    Test publishing environmental data to an existing device.
    Should return 201 Created if the device exists.
    """
    response = client.post(
        "/device/publish/env",
        json={
            "mac_addr": test_device.mac_addr,
            "type": "moisture",
            "value": 3.3
        }
    )

    assert response.status_code == 201


def test_duplicate_device_add(client):
    """
    Test that attempting to add a device with a duplicate MAC address
    will result in an error (500 or 409).
    """
    mac = generate_esp32_mac()

    valid_in = client.post(
        "/device/add/manf", 
        json={
            "mac_addr": mac
        }
    )
    assert valid_in.status_code == 201

    invalid_in = client.post(
        "/device/add/manf", 
        json={
            "mac_addr": mac
        }
    )
    assert invalid_in.status_code == 500 or invalid_in.status_code == 409


def test_invalid_mac_length(client):
    """
    Test that sending a MAC address shorter than 12 characters returns 422.
    """
    short_mac = "abc123"

    response = client.post(
        "/device/add/manf", 
        json={
            "mac_addr": short_mac
        }
    )

    assert response.status_code == 422


def test_data_publish_invalid_type(client, test_device):
    """
    Test that publishing data with an invalid sensor type
    (not 'ph' or 'moisture') returns 422.
    """
    response = client.post(
        "/device/publish/env", 
        json={
            "mac_addr": test_device.mac_addr,
            "type": "invalid_type",
            "value": 2.5
        }
    )

    assert response.status_code == 422


def test_data_publish_unknown_mac(client):
    """
    Test that publishing data to a MAC address not in the database
    returns a 404 Not Found response.
    """
    mac = generate_esp32_mac()

    response = client.post(
        "/device/publish/env", 
        json={
            "mac_addr": mac,
            "type": "ph",
            "value": 7.0
        }
    )

    assert response.status_code == 404


def test_data_publish_invalid_value_type(client, test_device):
    """
    Test publishing a non-float value (e.g., a string) for a float field.
    The API should reject this with a 422 Unprocessable Entity.
    """
    response = client.post(
        "/device/publish/env", 
        json={
            "mac_addr": test_device.mac_addr,
            "type": "ph",
            "value": "not_a_float"
        }
    )

    assert response.status_code == 422

def test_device_linking_with_fixture_user(client, test_teacher, test_device, test_class):
    """
    Test successful linking of a device to a class by a registered teacher 
    who is a member of the class.
    """
    register_resp = client.post(
        "/user/register",
        json={
            "first_name": test_teacher.first_name,
            "last_name": test_teacher.last_name,
            "password": test_teacher.password,
            "user_id": test_teacher.user_id,
            "user_type": test_teacher.user_type
        }
    )

    assert register_resp.status_code == 201
    
    login_resp = client.post("/user/login", data={
        "username": test_teacher.user_id,
        "password": test_teacher.password
    })

    assert login_resp.status_code == 200
    
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    join_resp = client.post(
        "/class/join", 
        json={
            "passphrase": test_class.passphrase
        }, 
        headers=headers)
    
    assert join_resp.status_code == 200

    response = client.post("/device/add/class", json={
        "mac_addr": test_device.mac_addr,
        "class_id": test_class.id
    }, headers=headers) ##add token to request

    assert response.status_code == 201


def test_link_nonexistent_device(client, test_teacher, test_class):
    """
    Test linking a non-existent device (invalid MAC address) to a class.
    Should return 404 Not Found.
    """
    client.post("/user/register", json={
        "first_name": test_teacher.first_name,
        "last_name": test_teacher.last_name,
        "password": test_teacher.password,
        "user_id": test_teacher.user_id,
        "user_type": test_teacher.user_type
    })

    login_resp = client.post("/user/login", data={
        "username": test_teacher.user_id,
        "password": test_teacher.password
    })
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/class/join", json={
        "passphrase": test_class.passphrase
    }, headers=headers)

    response = client.post("/device/add/class", json={
        "mac_addr": "djie3rtre323",  # Not in DB
        "class_id": test_class.id
    }, headers=headers)

    assert response.status_code == 404
    assert "does not exist" in response.json()["message"]

def test_link_device_to_nonexistent_class(client, test_teacher, test_device):
    """
    Test linking a valid device to a class that does not exist.
    Should return 404 Not Found.
    """
    client.post("/user/register", json={
        "first_name": test_teacher.first_name,
        "last_name": test_teacher.last_name,
        "password": test_teacher.password,
        "user_id": test_teacher.user_id,
        "user_type": test_teacher.user_type
    })

    login_resp = client.post("/user/login", data={
        "username": test_teacher.user_id,
        "password": test_teacher.password
    })
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_class_id = str(uuid.uuid4())

    response = client.post("/device/add/class", json={
        "mac_addr": test_device.mac_addr,
        "class_id": fake_class_id
    }, headers=headers)

    assert response.status_code == 404
    assert "Class not found" in response.json()["message"]

def test_unauthorized_user_cannot_link_device(client, test_student, test_device, test_class):
    """
    Test that a student who is neither a member nor the owner of a class 
    cannot link a device to that class.
    Should return 403 Forbidden.
    """
    # Register student (not owner or member)
    client.post("/user/register", json={
        "first_name": test_student.first_name,
        "last_name": test_student.last_name,
        "password": test_student.password,
        "user_id": test_student.user_id,
        "user_type": test_student.user_type
    })

    login_resp = client.post("/user/login", data={
        "username": test_student.user_id,
        "password": test_student.password
    })

    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Student has not joined the class
    response = client.post("/device/add/class", json={
        "mac_addr": test_device.mac_addr,
        "class_id": test_class.id
    }, headers=headers)

    assert response.status_code == 403
    assert "not authorized" in response.json()["message"]


def test_duplicate_device_linking(client, test_teacher, test_device, test_class):
    """
    Test that attempting to link a device to a class it's already linked to 
    returns a 409 Conflict response.
    """
    
    client.post("/user/register", json={
        "first_name": test_teacher.first_name,
        "last_name": test_teacher.last_name,
        "password": test_teacher.password,
        "user_id": test_teacher.user_id,
        "user_type": test_teacher.user_type
    })

    login_resp = client.post("/user/login", data={
        "username": test_teacher.user_id,
        "password": test_teacher.password
    })

    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Join class
    client.post("/class/join", json={
        "passphrase": test_class.passphrase
    }, headers=headers)

    # First successful link
    response1 = client.post("/device/add/class", json={
        "mac_addr": test_device.mac_addr,
        "class_id": test_class.id
    }, headers=headers)
    assert response1.status_code == 201

    # Duplicate link attempt
    response2 = client.post("/device/add/class", json={
        "mac_addr": test_device.mac_addr,
        "class_id": test_class.id
    }, headers=headers)

    assert response2.status_code == 409
    assert "already linked" in response2.json()["message"]
