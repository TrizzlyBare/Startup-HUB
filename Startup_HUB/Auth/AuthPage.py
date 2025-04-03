import reflex as rx
from typing import Optional
import httpx
from .base_state import BaseState

class AuthState(BaseState):
    """State for authentication."""
    # Form fields
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    email: str = ""
    password: str = ""
    show_login: bool = True
    
    # Error and success messages
    error: Optional[str] = None
    success: Optional[str] = None
    
    # Loading state
    is_loading: bool = False
    
    # Profile picture field
    profile_picture: Optional[str] = None
    _upload_data: Optional[bytes] = None

    # API endpoints
    API_BASE_URL = "http://127.0.0.1:8000/api/auth"
    
    def clear_messages(self):
        """Clear error and success messages."""
        self.error = None
        self.success = None
    
    def clear_form(self):
        """Clear all form fields."""
        self.first_name = ""
        self.last_name = ""
        self.username = ""
        self.email = ""
        self.password = ""
        self.profile_picture = None
        self._upload_data = None
        self.clear_messages()

    async def handle_login(self):
        """Handle login form submission."""
        self.clear_messages()
        self.is_loading = True
        
        try:
            if not self.email or not self.password:
                raise Exception("Please fill in all fields.")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/login/",
                    json={
                        "email": self.email,
                        "password": self.password
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Store the token in local storage or state management
                    self.success = "Login successful!"
                    return rx.redirect("/profile")
                else:
                    error_data = response.json()
                    raise Exception(error_data.get("error", "Login failed. Please try again."))
            
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False

    async def handle_register(self):
        """Handle registration form submission."""
        self.clear_messages()
        self.is_loading = True
        
        try:
            # Validate required fields
            if not all([self.first_name, self.last_name, self.username, self.email, self.password]):
                raise Exception("Please fill in all fields.")
            
            # Validate email format
            if "@" not in self.email or "." not in self.email:
                raise Exception("Please enter a valid email address.")
            
            # Validate password strength
            if len(self.password) < 8:
                raise Exception("Password must be at least 8 characters long.")
            
            # Prepare form data
            form_data = {
                "first_name": self.first_name,
                "last_name": self.last_name,
                "username": self.username,
                "email": self.email,
                "password": self.password
            }
            
            # If there's a profile picture, add it to the form data
            files = {}
            if self._upload_data:
                files["profile_picture"] = ("profile.jpg", self._upload_data, "image/jpeg")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/register/",
                    data=form_data,
                    files=files
                )
                
                if response.status_code == 201:
                    self.success = "Registration successful! Please login."
                    self.show_login = True
                    self.clear_form()
                else:
                    error_data = response.json()
                    # Handle specific error cases
                    if "email" in error_data:
                        raise Exception("This email is already registered. Please use a different email or login.")
                    elif "username" in error_data:
                        raise Exception("This username is already taken. Please choose a different username.")
                    elif "password" in error_data:
                        raise Exception("Password is too weak. Please use a stronger password.")
                    else:
                        error_message = error_data.get("error", "Registration failed. Please try again.")
                        raise Exception(error_message)
            
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False

    async def handle_forgot_password(self):
        """Handle forgot password request."""
        self.clear_messages()
        self.is_loading = True
        
        try:
            if not self.email:
                raise Exception("Please enter your email address.")
            
            # TODO: Implement forgot password endpoint
            self.success = "If an account exists with this email, password reset instructions will be sent."
            
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False
    
    def toggle_form(self):
        """Toggle between login and registration forms."""
        self.show_login = not self.show_login
        self.clear_form()

def login_form() -> rx.Component:
    return rx.vstack(
        rx.text("Welcome back", class_name="text-gray-600 text-sm"),
        rx.text("Login to your account", class_name="text-2xl font-bold text-gray-900 mb-6"),

        # Error and success messages
        rx.cond(
            AuthState.error,
            rx.text(AuthState.error, class_name="text-red-500 text-sm"),
            rx.text("", class_name="hidden"),
        ),
        rx.cond(
            AuthState.success,
            rx.text(AuthState.success, class_name="text-green-500 text-sm"),
            rx.text("", class_name="hidden"),
        ),

        rx.input(
            placeholder="Email Address",
            value=AuthState.email,
            on_change=AuthState.set_email,
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Password", 
            type="password",
            value=AuthState.password,
            on_change=AuthState.set_password,
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.hstack(
            rx.checkbox("Remember me", class_name="text-gray-700"),
            rx.spacer(),
            rx.link(
                "Forgot Password?",
                on_click=AuthState.handle_forgot_password,
                class_name="text-blue-600 text-sm hover:text-blue-700 cursor-pointer"
            ),
            width="100%",
        ),

        rx.button(
            rx.cond(
                AuthState.is_loading,
                rx.spinner(),
                rx.text("Login now"),
            ),
            class_name="bg-blue-600 text-white w-full py-2 rounded-lg font-semibold text-base hover:bg-blue-700 transition-colors",
            on_click=AuthState.handle_login,
            is_loading=AuthState.is_loading
        ),

        rx.text(
            "Don't have an account? ",
            rx.link(
                "Join free today", 
                on_click=AuthState.toggle_form,
                class_name="text-blue-600 font-semibold cursor-pointer"
            ),
            class_name="text-center text-gray-600 text-sm"
        ),

        spacing="4", 
        class_name="w-full max-w-md p-8"
    )

def signup_form() -> rx.Component:
    return rx.vstack(
        rx.text("Get Started", class_name="text-gray-600 text-sm"),
        rx.text("Create your account", class_name="text-2xl font-bold text-gray-900 mb-6"),

        # Error and success messages
        rx.cond(
            AuthState.error,
            rx.text(AuthState.error, class_name="text-red-500 text-sm"),
            rx.text("", class_name="hidden"),
        ),
        rx.cond(
            AuthState.success,
            rx.text(AuthState.success, class_name="text-green-500 text-sm"),
            rx.text("", class_name="hidden"),
        ),

        rx.hstack(
            rx.input(
                placeholder="First Name",
                value=AuthState.first_name,
                on_change=AuthState.set_first_name,
                class_name="flex-1 px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
            ),
            rx.input(
                placeholder="Last Name",
                value=AuthState.last_name,
                on_change=AuthState.set_last_name,
                class_name="flex-1 px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
            ),
            width="100%",
            spacing="4",
        ),

        rx.input(
            placeholder="Username",
            value=AuthState.username,
            on_change=AuthState.set_username,
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Email Address",
            value=AuthState.email,
            on_change=AuthState.set_email,
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Password",
            type="password",
            value=AuthState.password,
            on_change=AuthState.set_password,
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.button(
            rx.cond(
                AuthState.is_loading,
                rx.spinner(),
                rx.text("Sign up"),
            ),
            class_name="bg-blue-600 text-white w-full py-2 rounded-lg font-semibold text-base hover:bg-blue-700 transition-colors",
            on_click=AuthState.handle_register,
            is_loading=AuthState.is_loading
        ),

        rx.text(
            "Already have an account? ",
            rx.link(
                "Login here",
                on_click=AuthState.toggle_form,
                class_name="text-blue-600 font-semibold cursor-pointer"
            ),
            class_name="text-center text-gray-600 text-sm"
        ),

        spacing="4",
        class_name="w-full max-w-md p-8"
    )

def login_page() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left box - Image when login, Signup form when register
            rx.box(
                rx.cond(
                    AuthState.show_login,
                    rx.image(
                        src="/Logo.png",
                        class_name="w-full h-full object-cover"
                    ),
                    rx.box(
                        signup_form(),
                        class_name="flex items-center justify-center h-full bg-white"
                    )
                ),
                class_name="w-1/2 h-[600px] rounded-l-2xl overflow-hidden"
            ),
            
            # Right box - Login form when login, Image when register
            rx.box(
                rx.cond(
                    AuthState.show_login,
                    rx.box(
                        login_form(),
                        class_name="flex items-center justify-center h-full bg-white"
                    ),
                    rx.image(
                        src="/Logo.png",
                        class_name="w-full h-full object-cover"
                    )
                ),
                class_name="w-1/2 h-[600px] rounded-r-2xl overflow-hidden"
            ),
            
            class_name="w-full max-w-4xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden"
        ),
        class_name="min-h-screen flex justify-center items-center bg-gray-900 px-4"
    )

app = rx.App()
app.add_page(login_page)