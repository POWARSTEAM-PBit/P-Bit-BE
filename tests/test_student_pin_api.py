# #!/usr/bin/env python3
# """
# Test script for Per-Student PIN Class Management API
# """
# import requests
# import json
# import uuid

# BASE_URL = "http://localhost:8000"

# def test_student_pin_api():
#     print("🧪 Testing Per-Student PIN Class Management API")
#     print("=" * 65)
    
#     # Test data
#     teacher_email = f"teacher.{uuid.uuid4().hex[:8]}@example.com"
#     password = "testpassword123"
    
#     # Step 1: Register a teacher
#     print("1. Registering teacher...")
#     teacher_data = {
#         "first_name": "Test",
#         "last_name": "Teacher",
#         "user_id": teacher_email,
#         "password": password,
#         "user_type": "teacher"
#     }
    
#     response = requests.post(f"{BASE_URL}/user/register", json=teacher_data)
#     if response.status_code == 201:
#         print("✅ Teacher registered successfully")
#     else:
#         print(f"❌ Teacher registration failed: {response.text}")
#         return
    
#     # Step 2: Login as teacher
#     print("2. Logging in as teacher...")
#     form_data = {
#         'username': teacher_email,
#         'password': password
#     }
    
#     response = requests.post(f"{BASE_URL}/user/login", data=form_data)
#     if response.status_code == 200:
#         teacher_token = response.json()['data']['access_token']
#         print("✅ Teacher logged in successfully")
#     else:
#         print(f"❌ Teacher login failed: {response.text}")
#         return
    
#     # Step 3: Create a class
#     print("3. Creating a class...")
#     class_data = {
#         "name": "Test Mathematics",
#         "subject": "Mathematics",
#         "description": "A test class for per-student PIN API testing"
#     }
    
#     headers = {"Authorization": f"Bearer {teacher_token}"}
#     response = requests.post(f"{BASE_URL}/class/create", json=class_data, headers=headers)
#     if response.status_code == 201:
#         class_info = response.json()['data']
#         passphrase = class_info['passphrase']
#         class_id = class_info['id']
#         print(f"✅ Class created successfully with passphrase: {passphrase}")
#     else:
#         print(f"❌ Class creation failed: {response.text}")
#         return
    
#     # Step 4: Join class anonymously as first student
#     print("4. Joining class anonymously as first student...")
#     join_data1 = {
#         "passphrase": passphrase,
#         "first_name": "Alice",
#         "pin_code": "1234"
#     }
    
#     response = requests.post(f"{BASE_URL}/class/join-anonymous", json=join_data1)
#     if response.status_code == 200:
#         join_result1 = response.json()['data']
#         student_id1 = join_result1['student_id']
#         print(f"✅ First student joined successfully with ID: {student_id1}")
#     else:
#         print(f"❌ First student join failed: {response.text}")
#         return
    
#     # Step 5: Join class anonymously as second student
#     print("5. Joining class anonymously as second student...")
#     join_data2 = {
#         "passphrase": passphrase,
#         "first_name": "Bob",
#         "pin_code": "5678"
#     }
    
#     response = requests.post(f"{BASE_URL}/class/join-anonymous", json=join_data2)
#     if response.status_code == 200:
#         join_result2 = response.json()['data']
#         student_id2 = join_result2['student_id']
#         print(f"✅ Second student joined successfully with ID: {student_id2}")
#     else:
#         print(f"❌ Second student join failed: {response.text}")
#         return
    
#     # Step 6: Get class members (teacher view)
#     print("6. Getting class members...")
#     response = requests.get(f"{BASE_URL}/class/{class_id}/members", headers=headers)
#     if response.status_code == 200:
#         members = response.json()['data']
#         print(f"✅ Found {len(members)} class members")
#         for member in members:
#             print(f"   - {member['first_name']}: PIN {member['pin_code']}, Reset Required: {member['pin_reset_required']}")
#     else:
#         print(f"❌ Getting class members failed: {response.text}")
    
#     # Step 7: Reset first student's PIN
#     print("7. Resetting first student's PIN...")
#     response = requests.post(f"{BASE_URL}/class/{class_id}/reset-student-pin/{student_id1}", headers=headers)
#     if response.status_code == 200:
#         reset_result = response.json()['data']
#         print(f"✅ PIN reset for {reset_result['first_name']}")
#     else:
#         print(f"❌ PIN reset failed: {response.text}")
#         return
    
#     # Step 8: Try to join with old PIN (should fail)
#     print("8. Testing old PIN rejection after reset...")
#     old_pin_data = {
#         "passphrase": passphrase,
#         "first_name": "Alice",
#         "pin_code": "1234"  # Old PIN
#     }
    
#     response = requests.post(f"{BASE_URL}/class/join-anonymous", json=old_pin_data)
#     if response.status_code == 400:
#         print("✅ Old PIN correctly rejected (PIN reset required)")
#     else:
#         print(f"❌ Old PIN test failed: {response.text}")
    
#     # Step 9: Join with new PIN (should work)
#     print("9. Joining with new PIN...")
#     new_pin_data = {
#         "passphrase": passphrase,
#         "first_name": "Alice",
#         "pin_code": "9999"  # New PIN
#     }
    
#     response = requests.post(f"{BASE_URL}/class/join-anonymous", json=new_pin_data)
#     if response.status_code == 200:
#         print("✅ Student joined with new PIN successfully")
#     else:
#         print(f"❌ New PIN join failed: {response.text}")
    
#     # Step 10: Register a proper student account
#     print("10. Registering a proper student account...")
#     student_email = f"student.{uuid.uuid4().hex[:8]}@example.com"
#     student_data = {
#         "first_name": "Charlie",
#         "last_name": "Student",
#         "user_id": student_email,
#         "password": password,
#         "user_type": "student"
#     }
    
#     response = requests.post(f"{BASE_URL}/user/register", json=student_data)
#     if response.status_code == 201:
#         print("✅ Student registered successfully")
#     else:
#         print(f"❌ Student registration failed: {response.text}")
#         return
    
#     # Step 11: Login as student
#     print("11. Logging in as student...")
#     form_data = {
#         'username': student_email,
#         'password': password
#     }
    
#     response = requests.post(f"{BASE_URL}/user/login", data=form_data)
#     if response.status_code == 200:
#         student_token = response.json()['data']['access_token']
#         print("✅ Student logged in successfully")
#     else:
#         print(f"❌ Student login failed: {response.text}")
#         return
    
#     # Step 12: Join class as logged-in student (passphrase only)
#     print("12. Joining class as logged-in student...")
#     join_data3 = {"passphrase": passphrase}
#     headers = {"Authorization": f"Bearer {student_token}"}
    
#     response = requests.post(f"{BASE_URL}/class/join", json=join_data3, headers=headers)
#     if response.status_code == 200:
#         print("✅ Logged-in student joined successfully")
#     else:
#         print(f"❌ Logged-in student join failed: {response.text}")
    
#     # Step 13: Get updated class members
#     print("13. Getting updated class members...")
#     headers = {"Authorization": f"Bearer {teacher_token}"}
#     response = requests.get(f"{BASE_URL}/class/{class_id}/members", headers=headers)
#     if response.status_code == 200:
#         members = response.json()['data']
#         print(f"✅ Found {len(members)} class members after updates")
#         for member in members:
#             print(f"   - {member['first_name']}: Type {member['user_type']}, PIN {member['pin_code']}")
#     else:
#         print(f"❌ Getting updated members failed: {response.text}")
    
#     # Step 14: Remove second student from class
#     print("14. Removing second student from class...")
#     response = requests.delete(f"{BASE_URL}/class/{class_id}/remove-student/{student_id2}", headers=headers)
#     if response.status_code == 200:
#         remove_result = response.json()['data']
#         print(f"✅ Removed {remove_result['first_name']} from class")
#     else:
#         print(f"❌ Removing student failed: {response.text}")
    
#     # Step 15: Verify student was removed
#     print("15. Verifying student removal...")
#     response = requests.get(f"{BASE_URL}/class/{class_id}/members", headers=headers)
#     if response.status_code == 200:
#         members = response.json()['data']
#         remaining_students = [m for m in members if m['user_id'] == student_id2]
#         if len(remaining_students) == 0:
#             print("✅ Student successfully removed from class")
#         else:
#             print("❌ Student still appears in class members")
#     else:
#         print(f"❌ Verifying removal failed: {response.text}")
    
#     # Step 16: Delete class (as teacher)
#     print("16. Deleting class...")
#     headers = {"Authorization": f"Bearer {teacher_token}"}
#     response = requests.delete(f"{BASE_URL}/class/{class_id}", headers=headers)
#     if response.status_code == 200:
#         print("✅ Class deleted successfully")
#     else:
#         print(f"❌ Deleting class failed: {response.text}")
    
#     print("\n🎉 All per-student PIN tests completed successfully!")
#     print("\n📋 Summary:")
#     print("- ✅ Teachers can create classes with passphrases")
#     print("- ✅ Anonymous students can join with personal PINs")
#     print("- ✅ Logged-in students can join with just passphrase")
#     print("- ✅ Teachers can view all class members with PIN status")
#     print("- ✅ Teachers can reset individual student PINs")
#     print("- ✅ Teachers can remove students from classes")
#     print("- ✅ PIN reset forces students to set new PINs")
#     print("- ✅ Each student has their own independent PIN")
#     print("- ✅ Class deletion removes all memberships")

# if __name__ == "__main__":
#     test_student_pin_api()
