import reflex as rx

class AuthState(rx.State):
    """State for managing authentication."""
    
    # State variables
    token: str = ""
    is_authenticated: bool = False
    user: dict = {}
    
    def on_mount(self):
        """Load token from localStorage on mount."""
        return self.load_token()
    
    async def load_token(self):
        """Load token from localStorage."""
        # Get token from localStorage without using await
        token = rx.call_script("localStorage.getItem('auth_token')")
        
        # Don't assign EventSpec to self.token
        if token and not hasattr(token, 'event_spec'):
            self.token = token
            self.is_authenticated = True
            # Load user data
            await self.load_user_data()
    
    async def get_token(self):
        """Get the token from localStorage or state."""
        if self.token:
            return self.token
        
        # Get token from localStorage without using await
        token = rx.call_script("localStorage.getItem('auth_token')")
        
        # Don't assign EventSpec to self.token
        if token and not hasattr(token, 'event_spec'):
            self.token = token
            self.is_authenticated = True
            return token
        
        return ""
    
    async def load_user_data(self):
        """Load user data from the API."""
        if not self.token or self.token == "token_placeholder":
            return
        
        try:
            async with rx.utils.http.AsyncClient() as client:
                response = await client.get(
                    "http://100.95.107.24:8000/api/auth/user/",
                    headers={"Authorization": f"Token {self.token}"}
                )
                
                if response.status_code == 200:
                    self.user = response.json()
                else:
                    # Token is invalid, clear it
                    self.token = ""
                    self.is_authenticated = False
                    self.user = {}
                    # Use rx.call_script without await
                    rx.call_script("localStorage.removeItem('auth_token')")
        except Exception as e:
            print(f"Error loading user data: {str(e)}")
            # Clear token on error
            self.token = ""
            self.is_authenticated = False
            self.user = {}
            # Use rx.call_script without await
            rx.call_script("localStorage.removeItem('auth_token')")
    
    async def login(self, username: str, password: str):
        """Login with username and password."""
        try:
            async with rx.utils.http.AsyncClient() as client:
                response = await client.post(
                    "http://100.95.107.24:8000/api/auth/login/",
                    json={"username": username, "password": password}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("token", "")
                    self.is_authenticated = True
                    # Save token to localStorage
                    # Use rx.call_script without await
                    rx.call_script(f"localStorage.setItem('auth_token', '{self.token}')")
                    # Load user data
                    await self.load_user_data()
                    return True
                else:
                    return False
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False
    
    async def logout(self):
        """Logout the user."""
        self.token = ""
        self.is_authenticated = False
        self.user = {}
        # Use rx.call_script without await
        rx.call_script("localStorage.removeItem('auth_token')")
        return rx.redirect("/login") 