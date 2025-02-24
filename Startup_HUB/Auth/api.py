import httpx
from typing import Dict, Optional

# Update the base URL to match Django's default port
BASE_URL = "http://localhost:8000"

async def check_connection() -> bool:
    """Check if the API server is reachable."""
    try:
        async with httpx.AsyncClient() as client:
            # Check Django's admin endpoint to verify server is running
            response = await client.get(f"{BASE_URL}")
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        print(f"HTTP Exception: Server might be down or not running")
        raise Exception("Cannot connect to server. Please ensure the Django server is running.")

async def login(email: str, password: str) -> Dict:
    """Login user and return token."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/authen/login/",
                json={
                    "email": email,
                    "password": password
                }
            )
            if response.status_code == 404:
                raise Exception("Account not registered. Please create an account first.")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise Exception("Invalid email or password.")
        elif e.response.status_code == 404:
            raise Exception("Account not registered. Please create an account first.")
        else:
            print(f"Login error: {str(e)}")
            raise Exception("Login failed. Please try again.")
    except httpx.HTTPError as e:
        print(f"Connection error during login: {str(e)}")
        raise Exception("Cannot connect to server. Please try again later.")

async def register(
    first_name: str,
    last_name: str,
    username: str,
    email: str,
    password: str,
    profile_picture: Optional[bytes] = None
) -> Dict:
    """Register a new user with optional profile picture."""
    try:
        async with httpx.AsyncClient() as client:
            # Prepare form data
            form_data = {
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "email": email,
                "password": password,
            }
            
            files = {}
            if profile_picture:
                files["profile_picture"] = profile_picture

            response = await client.post(
                f"{BASE_URL}/api/authen/register/",
                data=form_data,
                files=files
            )
            
            if response.status_code == 409:
                raise Exception("Email or username already exists. Please login instead.")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise Exception("Email or username already exists. Please login instead.")
        elif e.response.status_code == 400:
            error_data = e.response.json()
            error_message = "Registration failed: "
            if isinstance(error_data, dict):
                for field, errors in error_data.items():
                    if isinstance(errors, list):
                        error_message += f"{field} - {errors[0]}. "
                    else:
                        error_message += f"{field} - {errors}. "
            raise Exception(error_message.strip())
        else:
            print(f"Registration error: {str(e)}")
            raise Exception("Registration failed. Please try again.")
    except httpx.HTTPError as e:
        print(f"Connection error during registration: {str(e)}")
        raise Exception("Cannot connect to server. Please try again later.")

async def forgot_password(email: str) -> Dict:
    """Send password reset email."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/auth/forgot-password/",
                json={"email": email}
            )
            if response.status_code == 404:
                raise Exception("Email not registered. Please create an account first.")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise Exception("Email not registered. Please create an account first.")
        else:
            print(f"Password reset error: {str(e)}")
            raise Exception("Failed to send reset email. Please try again.")
    except httpx.HTTPError as e:
        print(f"Connection error during password reset: {str(e)}")
        raise Exception("Cannot connect to server. Please try again later.") 