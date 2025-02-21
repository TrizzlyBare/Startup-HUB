import reflex as rx
from typing import Optional
from . import api
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
    
    # Loading and connection states
    is_loading: bool = False
    api_connected: bool = False
    
    # Add profile picture field
    profile_picture: Optional[bytes] = None

    async def check_api(self):
        """Check if API is reachable."""
        try:
            await api.check_connection()
            self.api_connected = True
            self.error = None
            return True
        except Exception as e:
            self.api_connected = False
            self.error = "Cannot connect to server. Please try again later."
            return False
    
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
        self.clear_messages()

    async def handle_login(self):
        """Handle login form submission."""
        self.clear_messages()
        self.is_loading = True
        
        try:
            # Check API connection first
            if not await self.check_api():
                return

            if not self.email or not self.password:
                raise Exception("Please fill in all fields.")
            
            response = await api.login(self.email, self.password)
            
            # Store token
            self.set_token(response["token"])
            self.success = "Login successful!"
            
            # Redirect to profile page after successful login
            return rx.redirect("/profile")
            
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False

    def handle_profile_picture_upload(self, file: rx.UploadFile):
        """Handle profile picture upload"""
        self.profile_picture = file.contents

    async def handle_register(self):
        """Handle registration form submission with profile picture."""
        self.clear_messages()
        self.is_loading = True
        
        try:
            if not await self.check_api():
                return

            if not all([self.first_name, self.last_name, self.username, self.email, self.password]):
                raise Exception("Please fill in all fields.")
            
            response = await api.register(
                first_name=self.first_name,
                last_name=self.last_name,
                username=self.username,
                email=self.email,
                password=self.password,
                profile_picture=self.profile_picture
            )
            self.success = "Registration successful! Please login."
            self.show_login = True
            self.clear_form()
            
        except Exception as e:
            self.error = str(e)
        finally:
            self.is_loading = False

    async def handle_forgot_password(self):
        """Handle forgot password request."""
        self.clear_messages()
        self.is_loading = True
        
        try:
            # Check API connection first
            if not await self.check_api():
                return

            if not self.email:
                raise Exception("Please enter your email address.")
            
            response = await api.forgot_password(self.email)
            self.success = "Password reset instructions sent to your email."
            
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

        # Add profile picture upload
        rx.upload(
            rx.text("Upload Profile Picture"),
            accept={"image/*"},
            max_files=1,
            on_change=AuthState.handle_profile_picture_upload,
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300",
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
                        src="/mock-image.jpg",
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
                        src="/mock-image.jpg",
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