import reflex as rx

class State(rx.State):
    email: str = ""
    password: str = ""

    def login(self):
        print(f"Logging in with Email: {self.email} and Password: {self.password}")

def login_page() -> rx.Component:
    return rx.box(
        rx.center(
            rx.hstack(
                # Left: Image Section (Ensure the image is in `assets/`)
                rx.box(
                    rx.image(src="/image/mock-image.png", class_name="rounded-xl w-full h-full object-cover"),
                    class_name="w-1/2 hidden sm:block"  # Hide on mobile
                ),

                # Right: Enlarged Login Form
                rx.box(
                    rx.vstack(
                        rx.text("Welcome back", class_name="text-gray-500 text-lg"),
                        rx.text("Login to your account", class_name="text-2xl font-bold text-gray-900 mb-4"),

                        # Email Input
                        rx.input(placeholder="Email Address", on_change=State.set_email, class_name="w-full px-4 py-3 border rounded-lg text-lg"),

                        # Password Input
                        rx.input(placeholder="Password", type="password", on_change=State.set_password, class_name="w-full px-4 py-3 border rounded-lg text-lg"),

                        # Remember Me & Forgot Password
                        rx.hstack(
                            rx.checkbox("Remember me", class_name="text-gray-600"),
                            rx.link("Forgot Password?", href="#", class_name="text-blue-500 text-sm ml-auto")
                        ),

                        # Enlarged Login Button
                        rx.button("Login now", class_name="bg-blue-500 text-white w-full py-3 rounded-lg font-semibold text-lg", on_click=State.login),

                        # Sign-up link
                        rx.text(
                            "Don't have an account? ",
                            rx.link("Join free today", href="#", class_name="text-blue-500 font-semibold"),
                            class_name="text-center text-gray-600"
                        ),

                        spacing="5", class_name="p-8 w-full"
                    ),
                    class_name="w-full sm:w-1/2 bg-white p-10 rounded-2xl shadow-xl max-w-lg"  # Increased size
                ),
            ),
            class_name="w-full max-w-5xl bg-gray-900 p-8 rounded-xl shadow-2xl"
        ),
        class_name="h-screen flex justify-center items-center bg-gray-900 px-4"
    )

app = rx.App()
app.add_page(login_page)
