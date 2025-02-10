import reflex as rx

class State(rx.State):
    pass
    

def index() -> rx.Component:
    return rx.vstack(
        # Navbar
        rx.box(
            rx.text("Startup HUB", class_name="text-lg sm:text-xl font-semibold text-gray-900"),
            rx.hstack(
                rx.link("Home", class_name="text-gray-600 hover:text-gray-900 px-4 py-2"),
                rx.link("About", class_name="text-gray-600 hover:text-gray-900 px-4 py-2"),
                rx.link("Co-Founders", class_name="text-gray-600 hover:text-gray-900 px-4 py-2"),
                rx.link("Contact", class_name="text-gray-600 hover:text-gray-900 px-4 py-2"),
                rx.link("Sign Up", class_name="text-white bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg font-semibold"),
                class_name="ml-auto"
            ),
            class_name="bg-white py-4 sm:py-6 px-6 w-full flex items-center"
        ),
        # Hero Section
        rx.box(
            rx.text("Find Your Perfect Co-Founder", class_name="text-3xl sm:text-5xl font-bold text-gray-900 mb-6"),
            rx.text(
                "Connect with passionate entrepreneurs who share your vision. Build your dream team and turn your startup idea into reality.", 
                class_name="text-lg sm:text-xl text-gray-600 mb-8 max-w-2xl mx-auto"
            ),
            class_name="relative text-center py-16 sm:py-24 bg-gradient-to-br from-purple-50 to-indigo-100 w-full px-6 justify-center items-center"
        ),
        
        # Stats Section (Responsive)
        rx.grid(
            *[
                rx.vstack(
                    rx.text(value, class_name="text-3xl sm:text-4xl font-bold text-indigo-600"), 
                    rx.text(label, class_name="text-gray-600 text-sm sm:text-base")
                ) 
                for value, label in [("10k+", "Entrepreneurs"), ("5k+", "Startups Formed"), ("50+", "Industries"), ("95%", "Match Rate")]
            ],
            columns=rx.breakpoints({"base": "2", "sm": "2", "md": "4"}),  
            spacing="6", class_name="border-y border-gray-100 bg-white py-12 w-full justify-center items-center"
        ),

        # How It Works Section
        rx.vstack(
            rx.text("How Startup HUB Works", class_name="text-2xl sm:text-3xl font-bold text-gray-900 mb-4 text-center"),
            rx.text("Find your perfect co-founder in three simple steps", class_name="text-gray-600 max-w-2xl mx-auto text-sm sm:text-base"),
            
            # Responsive Grid Layout
            rx.grid(
                *[
                    rx.box(
                        rx.text(title, class_name="text-lg sm:text-xl font-semibold text-gray-900 mb-2"),
                        rx.text(description, class_name="text-gray-600 text-sm sm:text-base"),
                        class_name="bg-gray-50 p-6 rounded-xl hover:shadow-lg transition-shadow w-full justify-center items-center"
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
                columns=rx.breakpoints({"base": "1", "md": "2"}),  # Single column on mobile, two columns on medium+
                spacing="8",  # Adds spacing between items
                class_name="w-full max-w-6xl mx-auto justify-center items-center"  # Centers the grid in the container
            ),

            class_name="py-16 sm:py-24 bg-white px-6 w-full justify-center items-center"
        ),
        
        # Call to Action Section
        rx.box(
            rx.text("Ready to Find Your Co-Founder?", class_name="text-2xl sm:text-3xl font-bold text-white mb-4"),
            rx.text("Join thousands of entrepreneurs who have found their perfect match on Startup HUB.", 
                    class_name="text-indigo-100 mb-6 max-w-2xl mx-auto text-sm sm:text-base"),
            rx.button("Create Your Profile", class_name="bg-white text-indigo-600 px-6 sm:px-8 py-3 rounded-lg font-semibold w-full sm:w-auto"),
            class_name="bg-indigo-600 py-12 sm:py-16 text-center w-full px-6 justify-center items-center"
        ),

        # Footer
        rx.box(
            rx.text("\u00a9 2024 Startup HUB. All rights reserved.", class_name="text-gray-400 text-center text-sm"),
            class_name="bg-gray-900 py-6 sm:py-12 w-full justify-center items-center"
        ),
        class_name="min-h-screen bg-white w-full justify-center items-center"
    )

app = rx.App()
app.add_page(index)