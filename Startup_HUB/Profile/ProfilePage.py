import reflex as rx

class State(rx.State):
    email: str = ""
    password: str = ""

    # Editable fields
    name: str = "name"
    description: str = "..."
    details: str = "..."
    project: str = "..."
    experience: str = "..."

    # Toggles for edit mode
    edit_mode: bool = False

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode

    def save_changes(self):
        print(f"Saved: {self.name}, {self.description}, {self.details}, {self.project}, {self.experience}")
        self.edit_mode = False

    def set_name(self, value: str):
        self.name = value

    def set_description(self, value: str):
        self.description = value

    def set_details(self, value: str):
        self.details = value

    def set_project(self, value: str):
        self.project = value

    def set_experience(self, value: str):
        self.experience = value

def profile_page() -> rx.Component:
    return rx.box(
        rx.grid(
            # Profile Image
            rx.box(
                rx.image(
                    src="/mock-image.jpg",  # Add a fallback image if needed
                    class_name="rounded-full object-cover w-48 h-48 border-4 border-white"
                )
            ),
            # Box containing Name and Description
            rx.box(
                # Update the greeting with the name
                rx.text(f"Hello, {State.name}", class_name="text-lg sm:text-xl font-bold text-gray-600"),
                rx.cond(
                    State.edit_mode,
                    rx.input(value=State.name, on_change=lambda value: State.set_name(value)),
                    rx.text(State.name, class_name="text-lg font-bold mb-2 text-color-black")
                ),
                rx.cond(
                    State.edit_mode,
                    rx.text_area(value=State.description, on_change=lambda value: State.set_description(value)),
                    rx.text(State.description, class_name="text-lg font-bold mb-2")
                ),
                class_name="bg-sky-200 p-4 rounded-lg shadow-md"
            ),

            # "Details" Card
            rx.box(
                rx.text("Details :", class_name="text-lg sm:text-xl font-bold text-gray-600"),
                rx.cond(
                    State.edit_mode,
                    rx.text_area(value=State.details, on_change=lambda value: State.set_details(value)),
                    rx.text(State.details, class_name="text-lg font-bold mb-2")
                ),
                class_name="bg-sky-200 p-4 rounded-lg shadow-md"
            ),
            # "Project" Card
            rx.box(
                rx.text("Projects :", class_name="text-lg sm:text-xl font-bold text-gray-600"),
                rx.cond(
                    State.edit_mode,
                    rx.text_area(value=State.project, on_change=lambda value: State.set_project(value)),
                    rx.text(State.project, class_name="text-lg font-bold mb-2")
                ),
                class_name="bg-sky-200 p-4 rounded-lg shadow-md"
            ),
            # "Experience" Card
            rx.box(
                rx.text("Experience :", class_name="text-lg sm:text-xl font-bold text-gray-600"),
                rx.cond(
                    State.edit_mode,
                    rx.text_area(value=State.experience, on_change=lambda value: State.set_experience(value)),
                    rx.text(State.experience, class_name="text-lg font-bold mb-2")
                ),
                class_name="bg-sky-200 p-4 rounded-lg shadow-md"
            ),
            class_name="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto"
        ),
        rx.box(
            rx.cond(
                State.edit_mode,
                rx.box(
                    rx.button("Save", on_click=State.save_changes, class_name="bg-green-500 text-white px-4 py-2 rounded"),
                    rx.button("Cancel", on_click=State.toggle_edit_mode, class_name="bg-red-500 text-white px-4 py-2 rounded ml-2"),
                    class_name="flex space-x-4 mt-4"
                ),
                rx.button("Edit", on_click=State.toggle_edit_mode, class_name="bg-blue-500 text-white px-4 py-2 rounded mt-4")
            )
        ),
        class_name="min-h-screen flex flex-col items-center justify-center bg-gray-800 p-8"
    )

# Create the Reflex app
app = rx.App()
app.add_page(profile_page, route="/profile")
