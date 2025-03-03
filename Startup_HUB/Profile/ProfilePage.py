import reflex as rx
from ..Auth.AuthPage import AuthState

class State(rx.State):
    """State for the profile page."""
    
    # Basic Info
    name: str = "Nanashi Mumei"
    first_name: str = "Nanashi"
    last_name: str = "Mumei"
    job_title: str = "KFC Worker"
    experience_level: str = "1-3 years"
    category: str = "Technology"
    
    # About section
    about: str = ""
    
    # Skills (list for better management)
    skills: list = ["Product Management", "UX/UI", "Marketing"]
    new_skill: str = ""
    
    # Project
    project: str = "SE Library"
    
    # Online presence links
    linkedin_link: str = ""
    github_link: str = ""
    portfolio_link: str = ""
    
    # Edit mode toggle
    edit_mode: bool = False
    show_edit_form: bool = False

    def toggle_edit_mode(self):
        """Toggle edit mode on/off."""
        self.edit_mode = not self.edit_mode

    def toggle_edit_form(self):
        """Toggle edit form visibility."""
        self.show_edit_form = not self.show_edit_form

    def save_changes(self):
        """Save profile changes."""
        self.name = f"{self.first_name} {self.last_name}"
        self.edit_mode = False
        self.show_edit_form = False

    def cancel_edit(self):
        """Cancel editing."""
        self.show_edit_form = False

    def set_first_name(self, value: str):
        """Update first name field."""
        self.first_name = value

    def set_last_name(self, value: str):
        """Update last name field."""
        self.last_name = value

    def set_about(self, value: str):
        """Update about field."""
        self.about = value

    def set_category(self, value: str):
        """Update industry category."""
        self.category = value

    def set_experience_level(self, value: str):
        """Update experience level."""
        self.experience_level = value

    def set_linkedin_link(self, value: str):
        """Update LinkedIn URL."""
        self.linkedin_link = value

    def set_github_link(self, value: str):
        """Update GitHub URL."""
        self.github_link = value

    def set_portfolio_link(self, value: str):
        """Update portfolio website URL."""
        self.portfolio_link = value

    def set_new_skill(self, value: str):
        """Set new skill to be added."""
        self.new_skill = value

    def add_skill(self, key_event=None):
        """Add a new skill to the skills list.
        
        Args:
            key_event: The keyboard event, if triggered by a key press.
        """
        # Only proceed if it's not a key event or if the key is Enter
        if key_event is None or key_event.key == "Enter":
            if self.new_skill and self.new_skill not in self.skills:
                self.skills.append(self.new_skill)
                self.new_skill = ""

    def remove_skill(self, skill: str):
        """Remove a skill from the skills list."""
        if skill in self.skills:
            self.skills.remove(skill)

    @rx.var
    def has_about(self) -> bool:
        """Check if about text exists."""
        return len(self.about) > 0

def skill_badge(skill: str) -> rx.Component:
    """Create a badge for a skill."""
    return rx.badge(
        skill,
        class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-lg m-1"
    )

def edit_form() -> rx.Component:
    """Render the edit form."""
    return rx.box(
        rx.vstack(
            rx.heading("Create Your Profile", size="4"),
            rx.text("Complete your profile to connect with startups and founders", color="gray"),
            
            # Profile Photo Upload
            rx.vstack(
                rx.box(
                    rx.cond(
                        AuthState.profile_picture,
                        rx.image(
                            src=AuthState.profile_picture,
                            width="100%",
                            height="100%",
                            object_fit="cover",
                            border_radius="full"
                        ),
                        rx.center(
                            rx.icon("image", color="gray", size=24),
                            width="100%",
                            height="100%"
                        )
                    ),
                    width="120px",
                    height="120px",
                    border_radius="full",
                    bg="gray.100",
                    border="2px solid",
                    border_color="gray.200",
                    overflow="hidden"
                ),
                rx.button(
                    rx.hstack(
                        rx.icon("plus", size=16),
                        rx.text("Upload profile photo"),
                        spacing="1"
                    ),
                    variant="outline",
                    size="2",
                    color_scheme="blue",
                    margin_top="2",
                ),
                align="center",
                spacing="2",
                margin_bottom="6"
            ),
            
            # Name Fields
            rx.hstack(
                rx.vstack(
                    rx.text("First Name", font_weight="medium", size="2", align="left", width="100%"),
                    rx.input(
                        placeholder="First Name",
                        value=State.first_name,
                        on_change=State.set_first_name,
                        width="100%"
                    ),
                    width="100%",
                    align_items="start"
                ),
                rx.vstack(
                    rx.text("Last Name", font_weight="medium", size="2", align="left", width="100%"),
                    rx.input(
                        placeholder="Last Name",
                        value=State.last_name,
                        on_change=State.set_last_name,
                        width="100%"
                    ),
                    width="100%",
                    align_items="start"
                ),
                width="100%",
                spacing="4"
            ),
            
            # Industry & Experience
            rx.vstack(
                rx.heading("Industry & Experience", size="5", margin_top="6", margin_bottom="2"),
                rx.hstack(
                    rx.vstack(
                        rx.text("Industry", font_weight="medium", size="2", align="left", width="100%"),
                        rx.select(
                            ["Technology", "Finance", "Healthcare", "Education", "E-commerce", "Other"],
                            placeholder="Select industry",
                            value=State.category,
                            on_change=State.set_category,
                            width="100%"
                        ),
                        width="100%",
                        align_items="start"
                    ),
                    rx.vstack(
                        rx.text("Years of Experience", font_weight="medium", size="2", align="left", width="100%"),
                        rx.select(
                            ["< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
                            placeholder="Select experience",
                            value=State.experience_level,
                            on_change=State.set_experience_level,
                            width="100%"
                        ),
                        width="100%",
                        align_items="start"
                    ),
                    width="100%",
                    spacing="4"
                ),
                width="100%",
                align_items="start"
            ),
            
            # About Section
            rx.vstack(
                rx.heading("About", size="5", margin_top="6", margin_bottom="2"),
                rx.text_area(
                    placeholder="Tell us about yourself...",
                    value=State.about,
                    on_change=State.set_about,
                    width="100%",
                    min_height="120px"
                ),
                width="100%",
                align_items="start"
            ),
            
            # Skills Section
            rx.vstack(
                rx.heading("Skills", size="5", margin_top="6", margin_bottom="2"),
                rx.flex(
                    rx.foreach(
                        State.skills,
                        lambda skill: rx.hstack(
                            rx.text(skill),
                            rx.icon(
                                "x",
                                cursor="pointer",
                                on_click=lambda s=skill: State.remove_skill(s),
                                color="gray",
                                size=16
                            ),
                            bg="blue.100",
                            color="blue.700",
                            border_radius="full",
                            padding_x="3",
                            padding_y="1",
                            margin="1"
                        )
                    ),
                    wrap="wrap"
                ),
                rx.input(
                    placeholder="Add more skills...",
                    value=State.new_skill,
                    on_change=State.set_new_skill,
                    on_key_down=State.add_skill,
                    width="100%",
                    margin_top="2"
                ),
                width="100%",
                align_items="start"
            ),
            
            # Online Presence
            rx.vstack(
                rx.heading("Online Presence", size="5", margin_top="6", margin_bottom="2"),
                rx.hstack(
                    rx.icon("linkedin", color="gray"),
                    rx.input(
                        placeholder="LinkedIn URL",
                        value=State.linkedin_link,
                        on_change=State.set_linkedin_link,
                        width="100%"
                    ),
                    width="100%"
                ),
                rx.hstack(
                    rx.icon("github", color="gray"),
                    rx.input(
                        placeholder="GitHub URL",
                        value=State.github_link,
                        on_change=State.set_github_link,
                        width="100%"
                    ),
                    width="100%"
                ),
                rx.hstack(
                    rx.icon("globe", color="gray"),
                    rx.input(
                        placeholder="Portfolio Website",
                        value=State.portfolio_link,
                        on_change=State.set_portfolio_link,
                        width="100%"
                    ),
                    width="100%"
                ),
                width="100%",
                align_items="start",
                spacing="4"
            ),
            
            # Action Buttons
            rx.hstack(
                rx.button(
                    "Cancel",
                    on_click=State.cancel_edit,
                    variant="outline",
                    color_scheme="gray",
                    size="2"
                ),
                rx.button(
                    "Save Profile",
                    on_click=State.save_changes,
                    color_scheme="blue",
                    size="2"
                ),
                margin_top="8",
                width="100%",
                justify="end",
                spacing="4"
            ),
            
            width="100%",
            max_width="600px",
            margin="auto",
            padding="8",
            spacing="4",
            align_items="start"
        ),
        class_name="bg-white rounded-lg shadow-lg"
    )

def profile_page() -> rx.Component:
    """Render the profile page."""
    return rx.box(
        rx.cond(
            State.show_edit_form,
            edit_form(),
            rx.vstack(
                # Header with profile image and basic info
                rx.hstack(
                    # Profile Image
                    rx.image(
                        src=rx.cond(
                            AuthState.profile_picture,
                            AuthState.profile_picture,
                            "/assets/mock-image.jpg"
                        ),
                        class_name="rounded-full w-24 h-24 object-cover border-2 border-gray-200"
                    ),
                    # Basic Info
                    rx.vstack(
                        rx.heading(State.name, size="3"),
                        rx.hstack(
                            rx.text(f"Job: {State.job_title}"),
                            align_items="center",
                            spacing="2"
                        ),
                        rx.hstack(
                            rx.badge(
                                State.category,
                                class_name="bg-blue-100 text-blue-800 px-3 py-1 rounded-full"
                            ),
                            rx.badge(
                                State.experience_level,
                                class_name="bg-green-100 text-green-800 px-3 py-1 rounded-full"
                            ),
                            spacing="2"
                        ),
                        align_items="start",
                        spacing="2"
                    ),
                    rx.spacer(),
                    # Edit Profile Button
                    rx.button(
                        "Edit Profile",
                        on_click=State.toggle_edit_form,
                        class_name="px-4 py-2 bg-gray-800 text-white rounded-lg"
                    ),
                    width="100%",
                    padding="4",
                    spacing="4"
                ),
                
                # About Section
                rx.box(
                    rx.heading("About", size="4", margin_bottom="2"),
                    rx.cond(
                        State.has_about,
                        rx.text(State.about),
                        rx.text("No description provided.", class_name="text-gray-500 italic")
                    ),
                    width="100%",
                    padding="4",
                    class_name="bg-white rounded-lg shadow"
                ),
                
                # Skills Section
                rx.box(
                    rx.heading("Skill", size="4", margin_bottom="2"),
                    rx.flex(
                        rx.foreach(
                            State.skills,
                            skill_badge
                        ),
                        wrap="wrap",
                        gap="2"
                    ),
                    width="100%",
                    padding="4",
                    class_name="bg-white rounded-lg shadow"
                ),
                
                # Project Section
                rx.box(
                    rx.heading("Project", size="4", margin_bottom="2"),
                    rx.badge(
                        State.project,
                        class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-lg"
                    ),
                    width="100%",
                    padding="4",
                    class_name="bg-white rounded-lg shadow"
                ),
                
                # Online Presence Section
                rx.box(
                    rx.heading("Online Presence", size="4", margin_bottom="2"),
                    rx.vstack(
                        rx.cond(
                            State.linkedin_link != "",
                            rx.hstack(
                                rx.icon("linkedin"),
                                rx.link("LinkedIn", href=State.linkedin_link, is_external=True),
                                class_name="text-blue-600 hover:text-blue-800"
                            ),
                            rx.fragment()
                        ),
                        rx.cond(
                            State.github_link != "",
                            rx.hstack(
                                rx.icon("github"),
                                rx.link("GitHub", href=State.github_link, is_external=True),
                                class_name="text-blue-600 hover:text-blue-800"
                            ),
                            rx.fragment()
                        ),
                        rx.cond(
                            State.portfolio_link != "",
                            rx.hstack(
                                rx.icon("globe"),
                                rx.link("Portfolio", href=State.portfolio_link, is_external=True),
                                class_name="text-blue-600 hover:text-blue-800"
                            ),
                            rx.fragment()
                        ),
                        rx.cond(
                            (State.linkedin_link == "") & (State.github_link == "") & (State.portfolio_link == ""),
                            rx.text("No links provided.", class_name="text-gray-500 italic"),
                            rx.fragment()
                        ),
                        align_items="start",
                        spacing="2"
                    ),
                    width="100%",
                    padding="4",
                    class_name="bg-white rounded-lg shadow"
                ),
                
                width="100%",
                max_width="800px",
                margin="auto",
                padding="4",
                spacing="4"
            )
        ),
        class_name="min-h-screen bg-gray-50 py-8"
    )

# Create the Reflex app
app = rx.App()
app.add_page(profile_page, route="/profile")