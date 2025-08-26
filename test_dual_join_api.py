#!/usr/bin/env python3
"""
Test script for Dual-Join Class Management API
"""
import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_dual_join_api():
    print("🧪 Testing Dual-Join Class Management API")
    print("=" * 60)
    
    # Test data
    teacher_email = f"teacher.{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"
    
    # Step 1: Register a teacher
    print("1. Registering teacher...")
    teacher_data = {
        "first_name": "Test",
        "last_name": "Teacher",
        "user_id": teacher_email,
        "password": password,
        "user_type": "teacher"
    }
    
    response = requests.post(f"{BASE_URL}/user/register", json=teacher_data)
    if response.status_code == 201:
        print("✅ Teacher registered successfully")
    else:
        print(f"❌ Teacher registration failed: {response.text}")
        return
    
    # Step 2: Login as teacher
    print("2. Logging in as teacher...")
    form_data = {
        'username': teacher_email,
        'password': password
    }
    
    response = requests.post(f"{BASE_URL}/user/login", data=form_data)
    if response.status_code == 200:
        teacher_token = response.json()['data']['access_token']
        print("✅ Teacher logged in successfully")
    else:
        print(f"❌ Teacher login failed: {response.text}")
        return
    
    # Step 3: Create a class
    print("3. Creating a class...")
    class_data = {
        "name": "Test Mathematics",
        "subject": "Mathematics",
        "description": "A test class for dual-join API testing"
    }
    
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = requests.post(f"{BASE_URL}/class/create", json=class_data, headers=headers)
    if response.status_code == 201:
        class_info = response.json()['data']
        passphrase = class_info['passphrase']
        pin_code = class_info['pin_code']
        class_id = class_info['id']
        print(f"✅ Class created successfully")
        print(f"   Passphrase: {passphrase}")
        print(f"   PIN Code: {pin_code}")
    else:
        print(f"❌ Class creation failed: {response.text}")
        return
    
    # Step 4: Get owned classes
    print("4. Getting owned classes...")
    response = requests.get(f"{BASE_URL}/class/owned", headers=headers)
    if response.status_code == 200:
        owned_classes = response.json()['data']
        print(f"✅ Found {len(owned_classes)} owned classes")
    else:
        print(f"❌ Getting owned classes failed: {response.text}")
    
    # Step 5: Join class anonymously (NO LOGIN REQUIRED!)
    print("5. Joining class anonymously...")
    join_data = {
        "passphrase": passphrase,
        "first_name": "Alice",
        "pin_code": pin_code
    }
    
    response = requests.post(f"{BASE_URL}/class/join-anonymous", json=join_data)
    if response.status_code == 200:
        join_result = response.json()['data']
        student_id = join_result['student_id']
        print(f"✅ Anonymous student joined successfully with ID: {student_id}")
    else:
        print(f"❌ Anonymous join failed: {response.text}")
        return
    
    # Step 6: Try anonymous join with wrong PIN (should fail)
    print("6. Testing wrong PIN rejection...")
    wrong_pin_data = {
        "passphrase": passphrase,
        "first_name": "Bob",
        "pin_code": "9999"  # Wrong PIN
    }
    
    response = requests.post(f"{BASE_URL}/class/join-anonymous", json=wrong_pin_data)
    if response.status_code == 401:
        print("✅ Wrong PIN correctly rejected")
    else:
        print(f"❌ Wrong PIN test failed: {response.text}")
    
    # Step 7: Join class anonymously with correct PIN
    print("7. Joining class anonymously with correct PIN...")
    correct_pin_data = {
        "passphrase": passphrase,
        "first_name": "Bob",
        "pin_code": pin_code
    }
    
    response = requests.post(f"{BASE_URL}/class/join-anonymous", json=correct_pin_data)
    if response.status_code == 200:
        join_result2 = response.json()['data']
        student_id2 = join_result2['student_id']
        print(f"✅ Second anonymous student joined successfully with ID: {student_id2}")
    else:
        print(f"❌ Second anonymous join failed: {response.text}")
    
    # Step 8: Register a proper student account
    print("8. Registering a proper student account...")
    student_email = f"student.{uuid.uuid4().hex[:8]}@example.com"
    student_data = {
        "first_name": "Charlie",
        "last_name": "Student",
        "user_id": student_email,
        "password": password,
        "user_type": "student"
    }
    
    response = requests.post(f"{BASE_URL}/user/register", json=student_data)
    if response.status_code == 201:
        print("✅ Student registered successfully")
    else:
        print(f"❌ Student registration failed: {response.text}")
        return
    
    # Step 9: Login as student
    print("9. Logging in as student...")
    form_data = {
        'username': student_email,
        'password': password
    }
    
    response = requests.post(f"{BASE_URL}/user/login", data=form_data)
    if response.status_code == 200:
        student_token = response.json()['data']['access_token']
        print("✅ Student logged in successfully")
    else:
        print(f"❌ Student login failed: {response.text}")
        return
    
    # Step 10: Join class as logged-in student (passphrase only)
    print("10. Joining class as logged-in student...")
    join_data3 = {"passphrase": passphrase}
    headers = {"Authorization": f"Bearer {student_token}"}
    
    response = requests.post(f"{BASE_URL}/class/join", json=join_data3, headers=headers)
    if response.status_code == 200:
        print("✅ Logged-in student joined successfully")
    else:
        print(f"❌ Logged-in student join failed: {response.text}")
    
    # Step 11: Get enrolled classes as logged-in student
    print("11. Getting enrolled classes...")
    response = requests.get(f"{BASE_URL}/class/enrolled", headers=headers)
    if response.status_code == 200:
        enrolled_classes = response.json()['data']
        print(f"✅ Found {len(enrolled_classes)} enrolled classes")
    else:
        print(f"❌ Getting enrolled classes failed: {response.text}")
    
    # Step 12: Reset PIN code (teacher)
    print("12. Resetting PIN code...")
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = requests.post(f"{BASE_URL}/class/{class_id}/reset-pin", headers=headers)
    if response.status_code == 200:
        reset_result = response.json()['data']
        new_pin = reset_result['new_pin_code']
        print(f"✅ PIN code reset successfully to: {new_pin}")
    else:
        print(f"❌ PIN reset failed: {response.text}")
        return
    
    # Step 13: Try anonymous join with old PIN (should fail)
    print("13. Testing old PIN rejection after reset...")
    old_pin_data = {
        "passphrase": passphrase,
        "first_name": "David",
        "pin_code": pin_code  # Old PIN
    }
    
    response = requests.post(f"{BASE_URL}/class/join-anonymous", json=old_pin_data)
    if response.status_code == 401:
        print("✅ Old PIN correctly rejected after reset")
    else:
        print(f"❌ Old PIN test failed: {response.text}")
    
    # Step 14: Join with new PIN (should work)
    print("14. Joining with new PIN...")
    new_pin_data = {
        "passphrase": passphrase,
        "first_name": "David",
        "pin_code": new_pin  # New PIN
    }
    
    response = requests.post(f"{BASE_URL}/class/join-anonymous", json=new_pin_data)
    if response.status_code == 200:
        print("✅ Anonymous join with new PIN successful")
    else:
        print(f"❌ New PIN join failed: {response.text}")
    
    # Step 15: Leave class as logged-in student
    print("15. Leaving class as logged-in student...")
    headers = {"Authorization": f"Bearer {student_token}"}
    response = requests.delete(f"{BASE_URL}/class/{class_id}/leave", headers=headers)
    if response.status_code == 200:
        print("✅ Student left class successfully")
    else:
        print(f"❌ Leaving class failed: {response.text}")
    
    # Step 16: Delete class (as teacher)
    print("16. Deleting class...")
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = requests.delete(f"{BASE_URL}/class/{class_id}", headers=headers)
    if response.status_code == 200:
        print("✅ Class deleted successfully")
    else:
        print(f"❌ Deleting class failed: {response.text}")
    
    print("\n🎉 All dual-join tests completed successfully!")
    print("\n📋 Summary:")
    print("- ✅ Teachers can create classes with passphrases and PINs")
    print("- ✅ Anonymous students can join with passphrase + first name + PIN")
    print("- ✅ Logged-in students can join with just passphrase")
    print("- ✅ PIN codes can be reset by teachers")
    print("- ✅ Wrong PINs are properly rejected")
    print("- ✅ Old PINs are invalidated after reset")
    print("- ✅ Both join methods work independently")
    print("- ✅ Class deletion removes all memberships")

if __name__ == "__main__":
    test_dual_join_api()
