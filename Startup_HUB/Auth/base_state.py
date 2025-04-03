import reflex as rx
from typing import Optional

class BaseState(rx.State):
    """Base state for the application with authentication handling."""

    # Auth token
    token: Optional[str] = None
    is_authed: bool = False
    
    def on_load(self):
        """Load token from localStorage when state is initialized."""
        return rx.call_script("""
            const token = localStorage.getItem('auth_token');
            if (token) {
                state.token = token;
                state.is_authed = true;
            }
        """)
    
    def check_auth(self) -> bool:
        """Check if user is authenticated."""
        return self.is_authed
    
    def set_token(self, token: str):
        """Set token in state and call the method to store in localStorage."""
        self.token = token
        self.is_authed = True if token else False
        # Call a separate method to handle localStorage (don't return it directly)
        self.store_token_in_local_storage(token)
    
    def store_token_in_local_storage(self, token: str):
        """Store token in localStorage (separate from the state update)."""
        return rx.call_script(f"""
            localStorage.setItem('auth_token', '{token}');
            console.log('Token saved to localStorage:', '{token}');
        """)

    def clear_token(self):
        """Clear token from storage and state."""
        self.token = None
        self.is_authed = False
        # Call a separate method to handle localStorage
        self.remove_token_from_local_storage()
    
    def remove_token_from_local_storage(self):
        """Remove token from localStorage (separate from the state update)."""
        return rx.call_script("""
            localStorage.removeItem('auth_token');
            console.log('Token removed from localStorage');
        """)

    def logout(self):
        """Logout user."""
        self.clear_token()
        # Call localStorage cleanup separately
        self.remove_token_from_local_storage()
        return rx.redirect("/login")

    def protect_route(self):
        """Protect route from unauthenticated access."""
        return rx.call_script("""
            const token = localStorage.getItem('auth_token');
            if (!token) {
                window.location.href = '/login';
            }
        """)

    def set_token_storage(self, token: str):
        """Set token in client storage."""
        self.set_client_storage("auth_token", token)

    def get_token_from_storage(self) -> Optional[str]:
        """Get token from client storage."""
        return self.get_client_storage("auth_token")

    def clear_token_storage(self):
        """Clear the token from client storage."""
        self.set_client_storage("auth_token", None) 