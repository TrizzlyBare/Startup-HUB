import reflex as rx
from typing import Optional

class BaseState(rx.State):
    """Base state for the application with authentication handling."""
    
    # Auth token
    token: Optional[str] = None
    is_authed: bool = False
    
    def check_auth(self) -> bool:
        """Check if user is authenticated."""
        token = self.get_token_from_cookie()
        if token is not None:
            self.token = token
            self.is_authed = True
            return True
        return False

    def set_token(self, token: str):
        """Set token in cookie and state."""
        self.token = token
        self.is_authed = True
        self.set_token_cookie(token)

    def clear_token(self):
        """Clear token from cookie and state."""
        self.token = None
        self.is_authed = False
        self.clear_token_cookie()

    def logout(self):
        """Logout user."""
        self.clear_token()
        return rx.redirect("/login")

    def protect_route(self):
        """Protect route from unauthenticated access."""
        token = self.get_token_from_cookie()
        if token is None:
            return rx.redirect("/login")

    def set_token_cookie(self, token: str):
        """Set token in an HTTP-only cookie."""
        rx.set_cookie("auth_token", token, httponly=True, max_age=7*24*60*60)  # 7 days

    def get_token_from_cookie(self) -> Optional[str]:
        """Get token from cookie."""
        return rx.get_cookie("auth_token")

    def clear_token_cookie(self):
        """Clear the token cookie."""
        rx.delete_cookie("auth_token") 