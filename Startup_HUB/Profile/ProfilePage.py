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
        # Main layout with profile image and content side-by-side
        rx.hstack(
            # Left Column: Profile Image and Project
            rx.vstack(
                # Profile Image Section
                rx.box(
                    rx.image(
                        src="/mock-image.jpg",
                        class_name="rounded-2xl object-cover w-80 h-80 border-4 border-white"
                    ),
                    class_name="mb-6"
                ),
                # Project Card
                rx.box(
                    rx.text("Projects :", class_name="text-xl sm:text-2xl font-bold text-black w-full bg-sky-300 p-4 rounded-2xl"),
                    rx.cond(
                        State.edit_mode,
                        rx.text_area(
                            value=State.project,
                            on_change=State.set_project,
                            placeholder="Enter project details",
                            class_name="w-full whitespace-normal resize-y "
                        ),
                        rx.text(State.project, class_name="text-l mb-2")
                    ),
                    class_name="bg-white p-4 rounded-2xl text-black shadow-md w-[350px] h-[200px]"
                ),
            ),
            # Right Column: Name, Details and Experience
            rx.vstack(
                # Name and Description Box
                rx.box(
                    rx.text(f"Meet, {State.name}", class_name="text-xl sm:text-2xl font-bold text-black w-full bg-sky-300 p-4 rounded-2xl"),
                    rx.cond(
                        State.edit_mode,
                        rx.input(
                            value=State.name,
                            on_change=State.set_name,
                            placeholder="Enter your name",
                            class_name="w-full mb-2"
                        ),
                    ),
                    rx.cond(
                        State.edit_mode,
                        rx.text_area(
                            value=State.description,
                            on_change=State.set_description,
                            placeholder="Enter a description",
                            class_name="w-full whitespace-normal resize-y min-h-[100px] max-h-[300px]"
                        ),
                        rx.text(State.description, class_name="text-l mb-2")
                    ),
                    class_name="bg-white p-4 rounded-2xl shadow-md text-black  w-[700px] h-auto"
                ),

                # Details Card
                rx.box(
                    rx.text("Details :", class_name="text-xl sm:text-2xl font-bold text-black w-full bg-sky-300 p-4 rounded-2xl"),
                    rx.cond(
                        State.edit_mode,
                        rx.text_area(
                            value=State.details,
                            on_change=State.set_details,
                            placeholder="Enter details",
                            class_name="w-full whitespace-normal resize-y"
                        ),
                        rx.text(State.details, class_name="text-l mb-2 text-black ")
                    ),
                    class_name="bg-white p-4 rounded-2xl shadow-md w-[700px] h-auto"
                ),

                # Experience Card
                rx.box(
                    rx.text("Experience :", class_name="text-xl sm:text-2xl font-bold text-black w-full bg-sky-300 p-4 rounded-2xl"),
                    rx.cond(
                        State.edit_mode,
                        rx.text_area(
                            value=State.experience,
                            on_change=State.set_experience,
                            placeholder="Enter your experience",
                            class_name="w-full whitespace-normal resize-y min-h-[100px] max-h-[300px]"
                        ),
                        rx.text(State.experience, class_name="text-l mb-2")
                    ),
                    class_name="bg-white p-4 rounded-2xl text-black  shadow-md w-[700px] h-[270px]"
                ),
                
                # Save and Edit Buttons
                rx.cond(
                    State.edit_mode,
                    rx.hstack(
                        rx.button("Save", on_click=State.save_changes, class_name="bg-green-500 text-white px-5 py-3 rounded"),
                        rx.button("Cancel", on_click=State.toggle_edit_mode, class_name="bg-red-500 text-white px-5 py-3 rounded ml-2"),
                        class_name="space-x-4 mt-4"
                    ),
                    rx.button("Edit", on_click=State.toggle_edit_mode, class_name="bg-blue-500 text-white px-5 py-3 rounded mt-4")
                ),
                class_name="space-y-6"  # Adds vertical spacing between sections
            ),
            class_name="space-x-10"  # Horizontal spacing between columns
        ),
        class_name="min-h-screen flex flex-col items-center justify-center bg-gray-800 p-10"
    )

# Create the Reflex app
app = rx.App()
app.add_page(profile_page, route="/profile")