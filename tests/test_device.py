import pytest
from db.db_models import Device
import secrets


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