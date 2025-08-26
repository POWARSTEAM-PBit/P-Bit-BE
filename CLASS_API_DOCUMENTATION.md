# Class Management API Documentation

## 🎓 Overview

The Class Management API provides comprehensive functionality for creating, joining, and managing educational classes. Teachers can create classes with unique passphrases, and students can join using either:

1. **Logged-in students**: Just enter passphrase → auto-join
2. **Anonymous students**: Enter passphrase + first name + 4-digit PIN → join

**Key Feature**: Each anonymous student has their own PIN code that teachers can reset and manage.

## 🔐 Authentication

**Teacher endpoints** require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

**Student join endpoints**:
- `/class/join` - Requires authentication (for logged-in students)
- `/class/join-anonymous` - No authentication required (for anonymous students)

## 📋 API Endpoints

### 1. Create Class
**POST** `/class/create`

Creates a new class owned by a teacher.

**Request Body:**
```json
{
  "name": "Advanced Mathematics",
  "subject": "Mathematics",
  "description": "Advanced calculus and linear algebra course"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Class created successfully",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Advanced Mathematics",
    "subject": "Mathematics",
    "description": "Advanced calculus and linear algebra course",
    "passphrase": "ABC12345",
    "owner_id": "teacher@example.com",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

**Requirements:**
- User must be a teacher (requires authentication)
- `name`: 1-100 characters
- `subject`: 1-100 characters
- `description`: Optional, max 1000 characters

---

### 2. Join Class (Logged-in Students)
**POST** `/class/join`

Joins a class using a passphrase. **Requires authentication.**

**Request Body:**
```json
{
  "passphrase": "ABC12345"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully joined Advanced Mathematics",
  "data": {
    "class_id": "550e8400-e29b-41d4-a716-446655440000",
    "class_name": "Advanced Mathematics",
    "subject": "Mathematics",
    "joined_at": "2024-01-15T11:00:00"
  }
}
```

**Requirements:**
- Valid passphrase
- User must be logged in (requires authentication)
- User not already a member of the class

---

### 3. Join Class Anonymously (No Login Required!)
**POST** `/class/join-anonymous`

Joins a class using a passphrase, first name, and personal PIN code. **No authentication required!**

**Request Body:**
```json
{
  "passphrase": "ABC12345",
  "first_name": "John",
  "pin_code": "1234"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully joined Advanced Mathematics",
  "data": {
    "class_id": "550e8400-e29b-41d4-a716-446655440000",
    "class_name": "Advanced Mathematics",
    "subject": "Mathematics",
    "student_id": "student_john_1705312800",
    "first_name": "John",
    "joined_at": "2024-01-15T11:00:00"
  }
}
```

**Requirements:**
- Valid passphrase
- Valid personal 4-digit PIN code
- `first_name`: 1-50 characters
- User not already a member of the class
- **No authentication required!**

**How it works:**
- Creates a temporary student account automatically
- Student ID format: `student_{firstname}_{timestamp}`
- Each student has their own PIN code
- If PIN reset is required, student must set a new PIN

---

### 4. Get Class Members (Teacher Only)
**GET** `/class/{class_id}/members`

Retrieves all members of a class with their details.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Class members retrieved successfully",
  "data": [
    {
      "user_id": "student_john_1705312800",
      "first_name": "John",
      "last_name": "",
      "user_type": "student",
      "joined_at": "2024-01-15T11:00:00",
      "pin_code": "1234",
      "pin_reset_required": false
    },
    {
      "user_id": "student_alice_1705312900",
      "first_name": "Alice",
      "last_name": "",
      "user_type": "student",
      "joined_at": "2024-01-15T11:05:00",
      "pin_code": "5678",
      "pin_reset_required": true
    }
  ]
}
```

**Requirements:**
- User must be the class owner (requires authentication)

---

### 5. Reset Student PIN (Teacher Only)
**POST** `/class/{class_id}/reset-student-pin/{student_id}`

Resets a specific student's PIN code, forcing them to set a new one.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Student PIN reset successfully",
  "data": {
    "student_id": "student_john_1705312800",
    "first_name": "John",
    "pin_reset_required": true
  }
}
```

**Requirements:**
- User must be the class owner (requires authentication)
- Student must be a member of the class

---

### 6. Remove Student from Class (Teacher Only)
**DELETE** `/class/{class_id}/remove-student/{student_id}`

Removes a specific student from the class.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Student removed from class successfully",
  "data": {
    "student_id": "student_john_1705312800",
    "first_name": "John",
    "class_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Requirements:**
- User must be the class owner (requires authentication)
- Student must be a member of the class

---

### 7. Get Owned Classes (Teachers)
**GET** `/class/owned`

Retrieves all classes owned by the current teacher.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Owned classes retrieved successfully",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Advanced Mathematics",
      "subject": "Mathematics",
      "description": "Advanced calculus and linear algebra course",
      "passphrase": "ABC12345",
      "owner_id": "teacher@example.com",
      "owner_name": "John Doe",
      "member_count": 15,
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

**Requirements:**
- User must be a teacher (requires authentication)

---

### 8. Get Enrolled Classes (Students)
**GET** `/class/enrolled`

Retrieves all classes where the current user is a member.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Enrolled classes retrieved successfully",
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Advanced Mathematics",
      "subject": "Mathematics",
      "description": "Advanced calculus and linear algebra course",
      "owner_id": "teacher@example.com",
      "owner_name": "John Doe",
      "member_count": 15,
      "joined_at": "2024-01-15T11:00:00",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

**Requirements:**
- User must be logged in (requires authentication)

---

### 9. Delete Class
**DELETE** `/class/{class_id}`

Deletes a class (only by the owner).

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Class deleted successfully",
  "data": null
}
```

**Requirements:**
- User must be the class owner (requires authentication)
- All class memberships are automatically removed

---

### 10. Leave Class
**DELETE** `/class/{class_id}/leave`

Removes the current user from a class.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully left the class",
  "data": null
}
```

**Requirements:**
- User must be a member of the class (requires authentication)
- Class owners cannot leave their own class (must delete instead)

---

## 🗄️ Database Schema

### Class Table
```sql
CREATE TABLE class (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    subject VARCHAR(100) NOT NULL,
    description TEXT,
    passphrase VARCHAR(12) UNIQUE NOT NULL,
    owner_id VARCHAR(64) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES user(user_id)
);
```

### ClassMember Table
```sql
CREATE TABLE class_member (
    id VARCHAR(36) PRIMARY KEY,
    class_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES class(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);
```

### User Table (Enhanced for Student PINs)
```sql
CREATE TABLE user (
    user_id VARCHAR(64) PRIMARY KEY,
    first_name VARCHAR(32) NOT NULL,
    last_name VARCHAR(32) NOT NULL,
    password VARCHAR(255) NOT NULL,  -- Empty for anonymous students
    user_type ENUM('student', 'teacher') NOT NULL,
    pin_code VARCHAR(4) NULL,  -- Personal PIN for anonymous students
    pin_reset_required BOOLEAN DEFAULT FALSE  -- Flag to force PIN reset
);
```

## 🔧 Passphrase & PIN Generation

### Passphrases
- **Length**: 8 characters
- **Characters**: Uppercase letters and numbers
- **Excluded**: Confusing characters (0, O, 1, I, L)
- **Uniqueness**: Guaranteed unique across all classes
- **Readability**: Easy to type and share

Example passphrases: `ABC12345`, `XYZ98765`, `DEF24680`

### Student PIN Codes
- **Length**: 4 digits
- **Characters**: Numbers only (0-9)
- **Per Student**: Each anonymous student has their own PIN
- **Resettable**: Teachers can reset individual student PINs
- **Required Reset**: Students must set new PIN when reset is required

Example PIN codes: `1234`, `5678`, `9012`

## 🚀 Frontend Integration Examples

### React/JavaScript Example
```javascript
// Create a class (requires teacher login)
const createClass = async (classData) => {
  const response = await fetch('http://localhost:8000/class/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(classData)
  });
  return response.json();
};

// Join class as logged-in student
const joinClass = async (passphrase) => {
  const response = await fetch('http://localhost:8000/class/join', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ passphrase })
  });
  return response.json();
};

// Join class anonymously (NO LOGIN REQUIRED!)
const joinClassAnonymous = async (passphrase, firstName, pinCode) => {
  const response = await fetch('http://localhost:8000/class/join-anonymous', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ 
      passphrase, 
      first_name: firstName,
      pin_code: pinCode
    })
  });
  return response.json();
};

// Get class members (teacher only)
const getClassMembers = async (classId) => {
  const response = await fetch(`http://localhost:8000/class/${classId}/members`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Reset student PIN (teacher only)
const resetStudentPin = async (classId, studentId) => {
  const response = await fetch(`http://localhost:8000/class/${classId}/reset-student-pin/${studentId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Remove student from class (teacher only)
const removeStudent = async (classId, studentId) => {
  const response = await fetch(`http://localhost:8000/class/${classId}/remove-student/${studentId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};
```

### cURL Examples
```bash
# Create a class (requires authentication)
curl -X POST http://localhost:8000/class/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Python Programming",
    "subject": "Computer Science",
    "description": "Learn Python from basics to advanced"
  }'

# Join class as logged-in student
curl -X POST http://localhost:8000/class/join \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"passphrase": "ABC12345"}'

# Join class anonymously (NO AUTHENTICATION REQUIRED!)
curl -X POST http://localhost:8000/class/join-anonymous \
  -H "Content-Type: application/json" \
  -d '{
    "passphrase": "ABC12345",
    "first_name": "Alice",
    "pin_code": "1234"
  }'

# Get class members
curl -X GET http://localhost:8000/class/CLASS_ID/members \
  -H "Authorization: Bearer YOUR_TOKEN"

# Reset student PIN
curl -X POST http://localhost:8000/class/CLASS_ID/reset-student-pin/STUDENT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# Remove student from class
curl -X DELETE http://localhost:8000/class/CLASS_ID/remove-student/STUDENT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🛡️ Security Features

1. **Role-based Access**: Only teachers can create classes and manage students
2. **Ownership Validation**: Only class owners can manage their classes
3. **Unique Passphrases**: Each class has a unique, easy-to-type passphrase
4. **Personal PIN Protection**: Each anonymous student has their own PIN
5. **PIN Reset Management**: Teachers can reset individual student PINs
6. **Dual Join System**: Support for both logged-in and anonymous students
7. **Automatic User Creation**: Temporary student accounts created on-demand
8. **Cascade Deletion**: Deleting a class removes all memberships
9. **Duplicate Prevention**: Users cannot join the same class twice
10. **Student Removal**: Teachers can remove students from their classes

## 🚨 Error Handling

Common error responses:

**403 Forbidden** - User not authorized
```json
{
  "success": false,
  "message": "Only teachers can create classes",
  "error": {"code": 403}
}
```

**404 Not Found** - Invalid passphrase or class not found
```json
{
  "success": false,
  "message": "Invalid passphrase",
  "error": {"code": 404}
}
```

**401 Unauthorized** - Invalid PIN code
```json
{
  "success": false,
  "message": "Invalid PIN code",
  "error": {"code": 401}
}
```

**400 Bad Request** - PIN reset required or already a member
```json
{
  "success": false,
  "message": "PIN reset required. Please set a new PIN code.",
  "error": {"code": 400}
}
```

## 🎯 Use Cases

### 1. **Teacher Workflow**:
   - Create class → Get passphrase → Share with students
   - View class members and their PIN status
   - Reset individual student PINs when needed
   - Remove problematic students from class
   - Delete classes when no longer needed

### 2. **Logged-in Student Workflow**:
   - Receive passphrase from teacher
   - Enter passphrase only → auto-join
   - View all enrolled classes
   - Leave classes when needed

### 3. **Anonymous Student Workflow**:
   - Receive passphrase and personal PIN from teacher
   - Enter first name, passphrase, and PIN → join
   - If PIN reset required, set new PIN before joining
   - No registration or login needed!
   - Quick access for temporary participation

### 4. **Class Management**:
   - Track class membership with detailed student info
   - Monitor PIN reset requirements
   - Manage individual student access
   - Support both persistent and temporary students

## 🔄 Student ID Generation

When students join anonymously, the system automatically creates a unique student ID:

**Format**: `student_{firstname}_{timestamp}`

**Examples**:
- `student_john_1705312800`
- `student_alice_1705312900`
- `student_bob_1705313000`

This ensures:
- Unique identification for each student
- No conflicts between students with same names
- Automatic cleanup when classes are deleted

## 📱 Frontend UI Considerations

### For Teachers:
- Display passphrase when creating classes
- Show class member list with PIN status
- Option to reset individual student PINs
- Option to remove students from class
- Show member counts for each class

### For Students:
- **Logged-in**: Simple passphrase input
- **Anonymous**: Three-field form (first name, passphrase, PIN)
- **PIN Reset**: Form to set new PIN when required
- Clear indication of which join method to use

### Security Notes:
- PIN codes should be shared securely (not in public channels)
- Teachers can reset PINs if compromised
- Passphrases are more public-friendly than PINs
- Each student has their own PIN for individual control
