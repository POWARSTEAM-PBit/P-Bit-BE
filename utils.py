from pydantic import BaseModel
from typing import Optional, Any

class error_resp(BaseModel):
    code: int
    details: Optional[str] = None

class api_resp(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[error_resp] = None



LOGIN_SUCCESS_RESPONSE = {
    "description": "Successful login, returns an API key",
    "content": {
        "application/json": {
            "example": {
                "success": True,
                "message": "Login successful",
                "data": {"api_key": "123e4567-e89b-12d3-a456-426614174000"},
                "error": None
            }
        }
    }
}

INVALID_EMAIL_RESPONSE = {
    "description": "Invalid email address",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Invalid email address: The email is not valid.",
                "data": None,
                "error": {"code": 400, "details": None}
            }
        }
    }
}

UNAUTHORIZED_RESPONSES = {
    "description": "Unauthorized: Invalid user type or wrong password",
    "content": {
        "application/json": {
            "examples": {
                "invalid_user_type": {
                    "summary": "Invalid user type",
                    "value": {
                        "success": False,
                        "message": "Invalid user type",
                        "data": None,
                        "error": {"code": 401, "details": None}
                    }
                },
                "wrong_password": {
                    "summary": "Incorrect password",
                    "value": {
                        "success": False,
                        "message": "Password is incorrect",
                        "data": None,
                        "error": {"code": 401, "details": None}
                    }
                }
            }
        }
    }
}

USER_NOT_FOUND_RESPONSE = {
    "description": "User does not exist",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "User does not exist",
                "data": None,
                "error": {"code": 404, "details": None}
            }
        }
    }
}