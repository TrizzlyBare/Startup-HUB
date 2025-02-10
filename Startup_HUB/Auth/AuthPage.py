import reflex as rx

class State(rx.State):
    email: str = ""
    password: str = ""

    def login(self):
        print(f"Logging in with Email: {self.email} and Password: {self.password}")

def login_page() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left side with illustration
            rx.box(
                rx.image(
                    src="/mock-image.jpg", 
                    class_name="w-full h-full object-cover rounded-l-2xl"
                ),
                class_name="w-1/2 h-[600px]"
            ),
            
            # Right side with login form
            rx.box(
                rx.vstack(
                    rx.text("Welcome back", class_name="text-gray-500 text-sm"),
                    rx.text("Login to your account", class_name="text-2xl font-bold text-gray-900 mb-6"),

                    # Email Input
                    rx.input(
                        placeholder="Email Address", 
                        on_change=State.set_email, 
                        class_name="w-full px-4 py-2 border rounded-lg text-base bg-gray-100 border-gray-300"
                    ),

                    # Password Input
                    rx.input(
                        placeholder="Password", 
                        type="password", 
                        on_change=State.set_password, 
                        class_name="w-full px-4 py-2 border rounded-lg text-base bg-gray-100 border-gray-300"
                    ),

                    # Remember Me & Forgot Password
                    rx.hstack(
                        rx.checkbox("Remember me", class_name="text-gray-600"),
                        rx.link("Forgot Password?", href="#", class_name="text-blue-500 text-sm ml-auto")
                    ),

                    # Login Button
                    rx.button(
                        "Login now", 
                        class_name="bg-blue-400 text-white w-full py-2 rounded-lg font-semibold text-base hover:bg-blue-500 transition-colors",
                        on_click=State.login
                    ),

                    # Sign-up link
                    rx.text(
                        "Don't have an account? ",
                        rx.link("Join free today", href="#", class_name="text-blue-500 font-semibold"),
                        class_name="text-center text-gray-600 text-sm"
                    ),

                    spacing="4", 
                    class_name="w-full max-w-md p-8"
                ),
                class_name="w-1/2 flex justify-center items-center bg-white rounded-r-2xl"
            ),
            
            class_name="w-full max-w-4xl mx-auto bg-white rounded-2xl shadow-xl overflow-hidden"
        ),
        class_name="min-h-screen flex justify-center items-center bg-gray-100 px-4"
    )

app = rx.App()
app.add_page(login_page)