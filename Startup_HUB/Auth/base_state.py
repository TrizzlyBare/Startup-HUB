import reflex as rx
from typing import Optional

class BaseState(rx.State):
    """Base state for the application with authentication handling."""

    # Auth token
    token: Optional[str] = None
    is_authed: bool = False
    
    # Client storage for auth token
    auth_token: str = rx.LocalStorage("")
    
    def check_auth(self) -> bool:
        """Check if user is authenticated."""
        token = self.auth_token
        if token:
            self.token = token
            self.is_authed = True
            return True
        return False

    def set_token(self, token: str):
        """Set token in storage and state."""
        self.token = token
        self.is_authed = True
        self.auth_token = token

    def clear_token(self):
        """Clear token from storage and state."""
        self.token = None
        self.is_authed = False
        self.auth_token = ""

    def logout(self):
        """Logout user."""
        self.clear_token()
        return rx.redirect("/login")

    def protect_route(self):
        """Protect route from unauthenticated access."""
        token = self.auth_token
        if not token:
            return rx.redirect("/login")

    def set_token_storage(self, token: str):
        """Set token in client storage."""
        self.set_client_storage("auth_token", token)

    def get_token_from_storage(self) -> Optional[str]:
        """Get token from client storage."""
        token = self.get_client_storage("auth_token")
        # Ensure we return a string token or None
        return token if isinstance(token, str) else None

    def clear_token_storage(self):
        """Clear the token from client storage."""
        self.set_client_storage("auth_token", None) 