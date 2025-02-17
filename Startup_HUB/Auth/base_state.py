import reflex as rx
from typing import Optional

class BaseState(rx.State):
    """Base state for the application with authentication handling."""
    
    # Auth token
    token: Optional[str] = None
    is_authed: bool = False
    
    def check_auth(self) -> bool:
        """Check if user is authenticated."""
        token = rx.get_local_storage("token")
        if token is not None:
            self.token = token
            self.is_authed = True
            return True
        return False

    def set_token(self, token: str):
        """Set token in local storage and state."""
        self.token = token
        self.is_authed = True
        rx.set_local_storage("token", token)

    def clear_token(self):
        """Clear token from local storage and state."""
        self.token = None
        self.is_authed = False
        rx.delete_local_storage("token")

    def logout(self):
        """Logout user."""
        self.clear_token()
        return rx.redirect("/login")

    def protect_route(self):
        """Protect route from unauthenticated access."""
        token = rx.get_local_storage("token")
        if token is None:
            return rx.redirect("/login") 