import reflex as rx
from typing import Optional
from ..Auth.AuthPage import AuthState

class MatchState(rx.State):
    """The app state."""
    active_tab: str = "Matches"
    selected_issue_type: str = ""
    selected_category: Optional[str] = None
    selected_id: Optional[str] = None
    profile_data: Optional[dict] = None
    is_authenticated: bool = False
    
    @rx.var
    def route_category(self) -> str:
        """Get category from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            match_type = params.get("match_type", "")
            if match_type:
                self.selected_category = match_type
                # You might want to change the active tab based on category
                if match_type in ["founders", "investors", "mentors"]:
                    self.active_tab = match_type.capitalize()
            return match_type
        return ""
    
    @rx.var
    def route_id(self) -> str:
        """Get ID from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            match_id = params.get("match_id", "")
            if match_id:
                self.selected_id = match_id
            return match_id
        return ""
    
    @rx.var
    def route_viewed_profile(self) -> str:
        """Get profile name from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            profile_name = params.get("user_profile", "")
            if profile_name:
                self.active_tab = "Profile Matches"
                # Here we would load the profile data based on the profile name
                # This is simplified for the example
                self.profile_data = {
                    "username": profile_name,
                    "fullname": profile_name.replace("_", " ").title(),
                    "skills": ["Python", "React", "Entrepreneurship"],
                    "interests": ["AI", "Blockchain", "SaaS"]
                }
                
                # In a real app, you'd fetch this data from an API
                print(f"Loading profile data for: {profile_name}")
            return profile_name
        return ""
    
    async def on_mount(self):
        """Called when the component mounts."""
        # Check authentication first
        auth_state = await self.get_state(AuthState)
        auth_token = auth_state.token
        
        # If no token in state, try localStorage
        if not auth_token:
            auth_token = rx.call_script("localStorage.getItem('auth_token')")
            
        # Set authentication status
        self.is_authenticated = bool(auth_token)
        
        # If not authenticated and on a protected route, redirect to login
        if not self.is_authenticated and hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            if params.get("user_profile"):
                return rx.redirect("/login?next=" + self.router.page.path)
        
        # Access route parameters
        self.route_category
        self.route_id
        self.route_viewed_profile

    def set_active_tab(self, tab: str):
        """Set the active tab."""
        self.active_tab = tab

    def set_selected_issue_type(self, issue_type: str):
        """Set the selected issue type."""
        self.selected_issue_type = issue_type 