import reflex as rx
import reflex_chakra as rc
from .Auth.AuthPage import login_page
from .Profile.ProfilePage import profile_page
from .Matcher.Matcher_Page import match_page

class State(rx.State):
    pass
    

def index() -> rx.Component:
    return rx.vstack(
        # Navbar
        rx.box(
            rx.text("Startup HUB", class_name="text-lg sm:text-xl font-semibold text-gray-900"),
            rx.hstack(
                rx.button("Home", class_name="text-gray-600 hover:text-gray-900 hover:underline px-4 py-2 bg-transparent", on_click=rx.redirect("/")),
                rx.button("About", class_name="text-gray-600 hover:text-gray-900 hover:underline px-4 py-2 bg-transparent", on_click=rx.redirect("/match")),
                rx.button("Co-Founders", class_name="text-gray-600 hover:text-gray-900 hover:underline px-4 py-2 bg-transparent"),
                rx.button("Contact", class_name="text-gray-600 hover:text-gray-900 hover:underline px-4 py-2 bg-transparent"),
                rx.button("Sign In", class_name="text-white bg-sky-900 hover:bg-cyan-600 px-4 py-2 rounded-lg font-semibold", on_click=rx.redirect("/login")),
                class_name="ml-auto"
            ),
            class_name="bg-white py-4 sm:py-6 px-6 w-full flex items-center"
        ),
        # Hero Section (Centered)
        rx.box(
            rx.text("Find Your Perfect Co-Founder", class_name="text-3xl sm:text-5xl font-bold text-neutral-50 mb-6 text-center"),
            rx.text(
                "Connect with passionate entrepreneurs who share your vision. Build your dream team and turn your startup idea into reality.", 
                class_name="text-lg sm:text-xl text-neutral-50 mb-8 max-w-2xl mx-auto text-center"
            ),
            class_name="relative text-center py-16 sm:py-24 bg-gradient-to-br from-sky-950 to-sky-900 w-full px-6 sm:px-12 flex flex-col items-center justify-center"
        ),

        # Stats Section (Centered & Responsive)
        rx.grid(
            *[
                rx.vstack(
                    rx.text(value, class_name="text-3xl sm:text-4xl font-bold text-cyan-600"), 
                    rx.text(label, class_name="text-gray-600 text-sm sm:text-base text-center"),
                    class_name="flex flex-col items-center text-center"
                ) 
                for value, label in [("10k+", "Entrepreneurs"), ("5k+", "Startups Formed"), ("50+", "Industries"), ("95%", "Match Rate")]
            ],
            columns=rx.breakpoints({"base": "2", "sm": "2", "md": "4"}),  
            spacing="9",  # Changed from "12" to "9" (valid range is "0" to "9")
            class_name="border-y border-gray-100 bg-white py-12 w-full max-w-6xl mx-auto flex justify-between items-center"
        ),

        # How It Works Section (Centered)
        rx.vstack(
            rx.text("How Startup HUB Works", class_name="text-2xl sm:text-3xl font-bold text-sky-900 mb-4 text-center"),
            rx.text("Find your perfect co-founder in three simple steps", class_name="text-gray-600 max-w-2xl mx-auto text-sm sm:text-base text-center"),
            
            # Responsive Grid Layout
            rx.grid(
                *[
                    rx.box(
                        rx.text(title, class_name="text-lg sm:text-xl font-semibold text-sky-900 mb-2 text-center"),
                        rx.text(description, class_name="text-gray-600 text-sm sm:text-base text-center"),
                        class_name="bg-gray-50 p-6 rounded-xl hover:shadow-lg transition-shadow w-full flex flex-col items-center justify-center"
                    ) 
                    for title, description in [
                        ("Share Your Vision", "Tell us about your startup idea and what kind of co-founder you're looking for."),
                        ("Match & Connect", "Our AI matches you with potential co-founders based on skills, interests, and goals."),
                        ("Collaborate", "Connect with matches, discuss ideas, and start building your startup together."),
                        ("Skill Alignment", "Find partners with complementary skills that match your startup needs."),
                        ("Secure Communication", "Chat securely with potential co-founders through our platform."),
                        ("Launch Together", "Get access to resources and guidance to launch your startup successfully.")
                    ]
                ],
                columns=rx.breakpoints({"base": "1", "md": "2"}),  
                spacing="8",  
                class_name="w-full max-w-6xl mx-auto justify-center items-center"
            ),

            class_name="py-16 sm:py-24 bg-white px-6 sm:px-12 w-full justify-center items-center"
        ),
        
        # Call to Action Section (Centered)
        rx.box(
            rx.text("Ready to Find Your Co-Founder?", class_name="text-2xl sm:text-3xl font-bold text-white mb-4 text-center"),
            rx.text("Join thousands of entrepreneurs who have found their perfect match on Startup HUB.", 
                    class_name="text-indigo-100 mb-6 max-w-2xl mx-auto text-sm sm:text-base text-center"),
            rx.button("Create Your Profile", class_name="bg-white text-cyan-600 px-6 sm:px-8 py-3 rounded-lg font-semibold w-full sm:w-auto"),
            class_name="bg-sky-900 py-12 sm:py-16 text-center w-full px-6 sm:px-12 flex flex-col items-center justify-center"
        ),

        # Footer (Centered)
        rx.box(
            rx.text("\u00a9 2024 Startup HUB. All rights reserved.", class_name="text-gray-400 text-center text-sm"),
            class_name="bg-gray-900 py-6 sm:py-12 w-full flex flex-col items-center justify-center"
        ),

        class_name="flex flex-col items-center justify-center min-h-screen bg-white w-full"
    )

app = rx.App()
app.add_page(index)
app.add_page(login_page, route="/login")
app.add_page(profile_page, route="/profile")
app.add_page(match_page, route="/match")
