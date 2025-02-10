import reflex as rx

class State(rx.State):
    email: str = ""
    password: str = ""
    show_login: bool = True  # Track which form to show
    
    def login(self):
        print(f"Logging in with Email: {self.email} and Password: {self.password}")
    
    def register(self):
        print(f"Registering with Email: {self.email} and Password: {self.password}")
    
    def toggle_form(self):
        self.show_login = not self.show_login
        self.email = ""
        self.password = ""

def login_form(State) -> rx.Component:
    return rx.vstack(
        rx.text("Welcome back", class_name="text-gray-600 text-sm"),
        rx.text("Login to your account", class_name="text-2xl font-bold text-gray-900 mb-6"),

        rx.input(
            placeholder="Email Address", 
            on_change=State.set_email, 
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Password", 
            type="password", 
            on_change=State.set_password, 
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.hstack(
            rx.checkbox("Remember me", class_name="text-gray-700"),
            rx.link("Forgot Password?", href="#", class_name="text-blue-600 text-sm ml-auto")
        ),

        rx.button(
            "Login now", 
            class_name="bg-blue-600 text-white w-full py-2 rounded-lg font-semibold text-base hover:bg-blue-700 transition-colors",
            on_click=State.login
        ),

        rx.text(
            "Don't have an account? ",
            rx.link(
                "Join free today", 
                on_click=State.toggle_form,
                class_name="text-blue-600 font-semibold cursor-pointer"
            ),
            class_name="text-center text-gray-600 text-sm"
        ),

        spacing="4", 
        class_name="w-full max-w-md p-8"
    )

def signup_form(State) -> rx.Component:
    return rx.vstack(
        rx.text("Get Started", class_name="text-gray-600 text-sm"),
        rx.text("Create your account", class_name="text-2xl font-bold text-gray-900 mb-6"),

        rx.input(
            placeholder="First Name", 
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Last Name", 
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Email Address", 
            on_change=State.set_email, 
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.input(
            placeholder="Password", 
            type="password", 
            on_change=State.set_password, 
            class_name="w-full px-4 py-2 border rounded-lg text-base bg-white border-gray-300 text-gray-900 placeholder-gray-500"
        ),

        rx.button(
            "Sign up", 
            class_name="bg-blue-600 text-white w-full py-2 rounded-lg font-semibold text-base hover:bg-blue-700 transition-colors",
            on_click=State.register
        ),

        rx.text(
            "Already have an account? ",
            rx.link(
                "Login here", 
                on_click=State.toggle_form,
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
                    State.show_login,
                    rx.image(
                        src="/mock-image.jpg", 
                        class_name="w-full h-full object-cover"
                    ),
                    rx.box(
                        signup_form(State),
                        class_name="flex items-center justify-center h-full bg-white"
                    )
                ),
                class_name="w-1/2 h-[600px] rounded-l-2xl overflow-hidden"
            ),
            
            # Right box - Login form when login, Image when register
            rx.box(
                rx.cond(
                    State.show_login,
                    rx.box(
                        login_form(State),
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