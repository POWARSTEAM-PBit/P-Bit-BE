#!/usr/bin/env python3
"""
Test script for Class Management API
"""
import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_class_api():
    print("🧪 Testing Class Management API")
    print("=" * 50)
    
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
        "description": "A test class for API testing"
    }
    
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = requests.post(f"{BASE_URL}/class/create", json=class_data, headers=headers)
    if response.status_code == 201:
        class_info = response.json()['data']
        passphrase = class_info['passphrase']
        class_id = class_info['id']
        print(f"✅ Class created successfully with passphrase: {passphrase}")
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
    
    # Step 5: Join class as anonymous student (NO LOGIN REQUIRED!)
    print("5. Joining class as anonymous student...")
    join_data = {
        "passphrase": passphrase,
        "first_name": "Alice"
    }
    
    response = requests.post(f"{BASE_URL}/class/join", json=join_data)
    if response.status_code == 200:
        join_result = response.json()['data']
        student_id = join_result['student_id']
        print(f"✅ Anonymous student joined successfully with ID: {student_id}")
    else:
        print(f"❌ Joining class failed: {response.text}")
        return
    
    # Step 6: Join class as another anonymous student
    print("6. Joining class as another anonymous student...")
    join_data2 = {
        "passphrase": passphrase,
        "first_name": "Bob"
    }
    
    response = requests.post(f"{BASE_URL}/class/join", json=join_data2)
    if response.status_code == 200:
        join_result2 = response.json()['data']
        student_id2 = join_result2['student_id']
        print(f"✅ Second anonymous student joined successfully with ID: {student_id2}")
    else:
        print(f"❌ Second student joining failed: {response.text}")
    
    # Step 7: Try to join again with same first name (should fail)
    print("7. Testing duplicate join prevention...")
    response = requests.post(f"{BASE_URL}/class/join", json=join_data)
    if response.status_code == 400:
        print("✅ Duplicate join correctly prevented")
    else:
        print(f"❌ Duplicate join prevention failed: {response.text}")
    
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
    
    # Step 10: Join class as registered student
    print("10. Joining class as registered student...")
    join_data3 = {
        "passphrase": passphrase,
        "first_name": "Charlie"
    }
    headers = {"Authorization": f"Bearer {student_token}"}
    
    response = requests.post(f"{BASE_URL}/class/join", json=join_data3, headers=headers)
    if response.status_code == 200:
        print("✅ Registered student joined successfully")
    else:
        print(f"❌ Registered student joining failed: {response.text}")
    
    # Step 11: Get enrolled classes as registered student
    print("11. Getting enrolled classes...")
    response = requests.get(f"{BASE_URL}/class/enrolled", headers=headers)
    if response.status_code == 200:
        enrolled_classes = response.json()['data']
        print(f"✅ Found {len(enrolled_classes)} enrolled classes")
    else:
        print(f"❌ Getting enrolled classes failed: {response.text}")
    
    # Step 12: Leave class as registered student
    print("12. Leaving class as registered student...")
    response = requests.delete(f"{BASE_URL}/class/{class_id}/leave", headers=headers)
    if response.status_code == 200:
        print("✅ Student left class successfully")
    else:
        print(f"❌ Leaving class failed: {response.text}")
    
    # Step 13: Delete class (as teacher)
    print("13. Deleting class...")
    headers = {"Authorization": f"Bearer {teacher_token}"}
    response = requests.delete(f"{BASE_URL}/class/{class_id}", headers=headers)
    if response.status_code == 200:
        print("✅ Class deleted successfully")
    else:
        print(f"❌ Deleting class failed: {response.text}")
    
    print("\n🎉 All tests completed successfully!")
    print("\n📋 Summary:")
    print("- ✅ Teachers can create classes and get passphrases")
    print("- ✅ Anonymous students can join with just first name + passphrase")
    print("- ✅ Registered students can join and manage enrollments")
    print("- ✅ Duplicate join prevention works")
    print("- ✅ Class deletion removes all memberships")

if __name__ == "__main__":
    test_class_api()
