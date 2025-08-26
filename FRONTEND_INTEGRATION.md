# Frontend Integration Guide - P-Bit Backend

## 🔐 Secure Authentication Flow

This guide shows how to integrate with the P-Bit backend using the secure OAuth2 approach.

## ⚠️ Important CORS & Credentials Note

**If you're using `credentials: 'include'` in your requests**, you need to:

1. **Use specific origins** (not wildcards) in CORS configuration ✅ (Already configured)
2. **Handle credentials properly** in your frontend requests

## 📋 API Endpoints

### 1. User Registration
```javascript
// Register a new user
const registerUser = async (userData) => {
  const response = await fetch('http://localhost:8000/user/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      first_name: userData.firstName,
      last_name: userData.lastName,
      user_id: userData.email, // email for teacher, username for student
      password: userData.password,
      user_type: userData.userType // "teacher" or "student"
    })
  });
  
  return response.json();
};
```

### 2. User Login (OAuth2 Form-based)
```javascript
// Login with OAuth2 form data
const loginUser = async (credentials) => {
  // Create form data (required for OAuth2 security)
  const formData = new URLSearchParams();
  formData.append('username', credentials.user_id);
  formData.append('password', credentials.password);
  
  const response = await fetch('http://localhost:8000/user/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData
    // Note: Don't use credentials: 'include' unless you need cookies
  });
  
  return response.json();
};
```

### 3. Get User Profile
```javascript
// Get user profile (requires authentication)
const getUserProfile = async (token) => {
  const response = await fetch('http://localhost:8000/user/profile', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  });
  
  return response.json();
};
```

## 🚀 Complete React Example

```jsx
import React, { useState } from 'react';

const AuthComponent = () => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  const handleRegister = async (userData) => {
    try {
      const response = await fetch('http://localhost:8000/user/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          first_name: userData.firstName,
          last_name: userData.lastName,
          user_id: userData.email,
          password: userData.password,
          user_type: 'teacher'
        })
      });

      const data = await response.json();
      
      if (data.success) {
        console.log('Registration successful!');
        // Optionally auto-login after registration
        await handleLogin({ user_id: userData.email, password: userData.password });
      } else {
        console.error('Registration failed:', data.message);
      }
    } catch (error) {
      console.error('Registration error:', error);
    }
  };

  const handleLogin = async (credentials) => {
    try {
      // Create form data for OAuth2
      const formData = new URLSearchParams();
      formData.append('username', credentials.user_id);
      formData.append('password', credentials.password);

      const response = await fetch('http://localhost:8000/user/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData
        // Don't use credentials: 'include' unless you need cookies
      });

      const data = await response.json();
      
      if (data.success) {
        setToken(data.data.access_token);
        // Store token in localStorage
        localStorage.setItem('token', data.data.access_token);
        // Fetch user profile
        await fetchUserProfile(data.data.access_token);
      } else {
        console.error('Login failed:', data.message);
      }
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  const fetchUserProfile = async (authToken) => {
    try {
      const response = await fetch('http://localhost:8000/user/profile', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      setUser(data);
    } catch (error) {
      console.error('Profile fetch error:', error);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    // Clear from localStorage if you're storing it there
    localStorage.removeItem('token');
  };

  return (
    <div>
      {!user ? (
        <div>
          <h2>Login</h2>
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            handleLogin({
              user_id: formData.get('email'),
              password: formData.get('password')
            });
          }}>
            <input name="email" type="email" placeholder="Email" required />
            <input name="password" type="password" placeholder="Password" required />
            <button type="submit">Login</button>
          </form>
        </div>
      ) : (
        <div>
          <h2>Welcome, {user.first_name}!</h2>
          <p>User ID: {user.user_id}</p>
          <p>User Type: {user.user_type}</p>
          <button onClick={handleLogout}>Logout</button>
        </div>
      )}
    </div>
  );
};

export default AuthComponent;
```

## 🔧 Axios Example

```javascript
import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  // Don't use withCredentials unless you need cookies
  // withCredentials: false
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// API functions
export const authAPI = {
  register: (userData) => api.post('/user/register', userData),
  
  login: (credentials) => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.user_id);
    formData.append('password', credentials.password);
    
    return api.post('/user/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
  
  getProfile: () => api.get('/user/profile'),
};
```

## 🛡️ Security Best Practices

1. **Store tokens securely**: Use `httpOnly` cookies or secure localStorage
2. **Token expiration**: Handle 401 responses and redirect to login
3. **CSRF protection**: The OAuth2 form-based approach provides this automatically
4. **HTTPS in production**: Always use HTTPS for authentication
5. **Input validation**: Validate all inputs on both frontend and backend

## 🧪 Testing

Test your integration with these curl commands:

```bash
# Register
curl -X POST http://localhost:8000/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "user_id": "test@example.com",
    "password": "password123",
    "user_type": "teacher"
  }'

# Login
curl -X POST http://localhost:8000/user/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123"

# Get Profile (replace TOKEN with actual token)
curl -X GET http://localhost:8000/user/profile \
  -H "Authorization: Bearer TOKEN"
```

## 🚨 Common Issues

1. **CORS errors**: Make sure your frontend origin is in the allowed origins
2. **422 errors**: Check that all required fields are provided
3. **401 errors**: Token might be expired or invalid
4. **Form data format**: Login must use `application/x-www-form-urlencoded`
5. **Credentials mode**: Don't use `credentials: 'include'` unless you need cookies

## 🔧 Fixing Your Current Issue

If you're getting the CORS error with `credentials: 'include'`, you have two options:

### Option 1: Remove credentials (Recommended)
```javascript
// Don't use credentials: 'include' for token-based auth
fetch('http://localhost:8000/user/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  body: formData
  // Remove credentials: 'include'
});
```

### Option 2: Use specific origin
If you must use `credentials: 'include'`, make sure your frontend is running on one of the allowed origins:
- `http://localhost:5173`
- `http://localhost:5174` ✅ (Now added)
- `http://127.0.0.1:5173`
- `http://127.0.0.1:5174` ✅ (Now added)
