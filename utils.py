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
    error_type: Optional[str] = None



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

REGISTER_SUCCESS_RESPONSE = {
    "description": "User registered successfully",
    "content": {
        "application/json": {
            "example": {
                "success": True,
                "message": "Register successful",
                "data": None,
                "error": None
            }
        }
    }
}

INVALID_EMAIL_REGISTER_RESPONSE = {
    "description": "Invalid email format (for teacher)",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Invalid email address",
                "data": None,
                "error": {"code": 422, "details": None}
            }
        }
    }
}

INVALID_USER_TYPE_REGISTER_RESPONSE = {
    "description": "Invalid user type",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Invalid user type",
                "data": None,
                "error": {"code": 401, "details": None}
            }
        }
    }
}

VALIDATION_ERROR_REGISTER_RESPONSES = {
    "description": "Validation or business logic error",
    "content": {
        "application/json": {
            "examples": {
                "user_exists": {
                    "summary": "User already exists",
                    "value": {
                        "success": False,
                        "message": "User already exists",
                        "data": None,
                        "error": {"code": 422, "details": None}
                    }
                },
                "missing_email": {
                    "summary": "Missing email for teacher",
                    "value": {
                        "success": False,
                        "message": "Email is required for teacher registration",
                        "data": None,
                        "error": {"code": 422, "details": None}
                    }
                },
                "missing_username": {
                    "summary": "Missing username for student",
                    "value": {
                        "success": False,
                        "message": "Username is required for student registration",
                        "data": None,
                        "error": {"code": 422, "details": None}
                    }
                }
            }
        }
    }
}

INTERNAL_SERVER_ERROR_REGISTER_RESPONSE = {
    "description": "Internal server error during registration",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Failed to register",
                "data": None,
                "error": {"code": 500, "details": None}
            }
        }
    }
}

# Validation utilities for anonymous students
def validate_pin_code(pin_code: str) -> tuple[bool, str]:
    """
    Validate PIN code format.
    Returns (is_valid, error_message)
    """
    if not pin_code:
        return False, "PIN code is required"
    
    if len(pin_code) != 4:
        return False, "PIN code must be exactly 4 digits"
    
    if not pin_code.isdigit():
        return False, "PIN code must contain only digits"
    
    return True, ""

def validate_first_name(first_name: str) -> tuple[bool, str]:
    """
    Validate first name format.
    Returns (is_valid, error_message)
    """
    if not first_name:
        return False, "First name is required"
    
    if len(first_name.strip()) == 0:
        return False, "First name cannot be empty"
    
    if len(first_name) > 50:
        return False, "First name must be 50 characters or less"
    
    return True, ""

def validate_passphrase(passphrase: str) -> tuple[bool, str]:
    """
    Validate classroom passphrase format.
    Expected format: ABCD-EFGH (4 letters - 4 letters)
    Returns (is_valid, error_message)
    """
    if not passphrase:
        return False, "Passphrase is required"
    
    # Check exact length (9 characters: 4 letters + hyphen + 4 letters)
    if len(passphrase) != 9:
        return False, "Passphrase must be exactly 9 characters (ABCD-EFGH format)"
    
    # Check format: ABCD-EFGH
    import re
    pattern = r'^[A-Z]{4}-[A-Z]{4}$'
    if not re.match(pattern, passphrase):
        return False, "Passphrase must be in format ABCD-EFGH (4 uppercase letters, hyphen, 4 uppercase letters)"
    
    return True, ""

# Device and Group validation utilities
def validate_mac_address(mac_address: str) -> tuple[bool, str]:
    """
    Validate MAC address format.
    Returns (is_valid, error_message)
    """
    import re
    
    if not mac_address:
        return False, "MAC address is required"
    
    # MAC address pattern: AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    
    if not re.match(pattern, mac_address):
        return False, "MAC address must be in format AA:BB:CC:DD:EE:FF or AA-BB-CC-DD-EE-FF"
    
    return True, ""

def validate_nickname(nickname: str) -> tuple[bool, str]:
    """
    Validate device nickname format.
    Returns (is_valid, error_message)
    """
    if not nickname:
        return False, "Nickname is required"
    
    if len(nickname.strip()) < 2:
        return False, "Nickname must be at least 2 characters"
    
    if len(nickname) > 20:
        return False, "Nickname must be 20 characters or less"
    
    return True, ""

def validate_group_name(name: str) -> tuple[bool, str]:
    """
    Validate group name format.
    Returns (is_valid, error_message)
    """
    if not name:
        return False, "Group name is required"
    
    if len(name.strip()) < 1:
        return False, "Group name cannot be empty"
    
    if len(name) > 100:
        return False, "Group name must be 100 characters or less"
    
    return True, ""

def validate_group_icon(icon: str) -> tuple[bool, str]:
    """
    Validate group icon format.
    Returns (is_valid, error_message)
    """
    if not icon:
        return False, "Group icon is required"
    
    if len(icon) > 10:
        return False, "Group icon must be 10 characters or less"
    
    return True, ""

def validate_assignment_type(assignment_type: str) -> tuple[bool, str]:
    """
    Validate device assignment type.
    Returns (is_valid, error_message)
    """
    valid_types = ['unassigned', 'student', 'group']
    
    if not assignment_type:
        return False, "Assignment type is required"
    
    if assignment_type not in valid_types:
        return False, f"Assignment type must be one of: {', '.join(valid_types)}"
    
    return True, ""

def validate_time_range(time_range: str) -> tuple[bool, str]:
    """
    Validate time range parameter.
    Returns (is_valid, error_message)
    """
    valid_ranges = ['1h', '6h', '24h', '7d', '30d']
    
    if not time_range:
        return True, ""  # Default will be used
    
    if time_range not in valid_ranges:
        return False, f"Time range must be one of: {', '.join(valid_ranges)}"
    
    return True, ""

def generate_passphrase() -> str:
    """
    Generate a unique, easy-to-type passphrase for classroom access.
    Returns an 8-character passphrase in format: ABCD-EFGH (4 letters - 4 letters).
    """
    import random
    import string
    
    # Use only uppercase letters for easy reading and typing
    letters = string.ascii_uppercase
    
    # Generate two groups of 4 letters each
    group1 = ''.join(random.choice(letters) for _ in range(4))
    group2 = ''.join(random.choice(letters) for _ in range(4))
    
    # Combine with hyphen: ABCD-EFGH
    passphrase = f"{group1}-{group2}"
    
    return passphrase
