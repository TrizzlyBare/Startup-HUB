import reflex as rx
from ..Auth.AuthPage import AuthState
import httpx

class State(rx.State):
    """State for the profile page."""
    
    # Basic Info
    name: str = "Nanashi Mumei"
    first_name: str = "Nanashi"
    last_name: str = "Mumei"
    job_title: str = "KFC Worker"
    experience_level: str = "1-3 years"
    category: str = "Technology"
    
    # Profile username (different from route parameter)
    profile_username: str = ""
    
    @rx.var
    def get_username(self) -> str:
        """Get username from route parameters."""
        if not self.profile_username and hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            self.profile_username = params.get("profile_name", "")
        return self.profile_username
    
    @rx.var
    def current_url(self) -> str:
        """Get the current full URL."""
        return self.router.page.full_raw_path

    async def on_mount(self):
        """Load profile data when component mounts."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            username = params.get("profile_name", "")
            if username:
                self.profile_username = username
                await self.load_profile_data()
            else:
                return rx.redirect("/")
    
    # About section
    about: str = ""
    
    # Skills (list for better management)
    skills: list = []
    new_skill: str = ""
    
    # Projects (list of projects)
    projects: list = []
    new_project: str = ""
    
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

    async def save_changes(self, form_data: dict):
        """Save profile changes to the API."""
        # Update profile data from form
        self.first_name = form_data.get("first_name", self.first_name)
        self.last_name = form_data.get("last_name", self.last_name)
        self.job_title = form_data.get("job_title", self.job_title)
        self.about = form_data.get("about", self.about)
        self.category = form_data.get("category", self.category)
        self.experience_level = form_data.get("experience_level", self.experience_level)
        self.linkedin_link = form_data.get("linkedin_link", self.linkedin_link)
        self.github_link = form_data.get("github_link", self.github_link)
        self.portfolio_link = form_data.get("portfolio_link", self.portfolio_link)
        
        # Compose full name
        self.name = f"{self.first_name} {self.last_name}"
        
        # Get username from router
        username = self.router.page.params.get("profile_name", "")
        if username:
            try:
                # Prepare data to send to API
                profile_data = {
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                    "job_title": self.job_title,
                    "about": self.about,
                    "category": self.category,
                    "experience_level": self.experience_level,
                    "skills": self.skills,
                    "projects": self.projects,
                    "linkedin_link": self.linkedin_link,
                    "github_link": self.github_link,
                    "portfolio_link": self.portfolio_link
                }
                
                # Make API call to update profile
                async with httpx.AsyncClient() as client:
                    response = await client.put(
                        f"http://127.0.0.1:8000/api/auth/profile/{username}",
                        json=profile_data
                    )
                    
                    if response.status_code != 200:
                        print(f"Error updating profile: {response.text}")
            except Exception as e:
                print(f"Error saving profile changes: {e}")
        
        # Close the form modal
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
        
    def set_new_project(self, value: str):
        """Set new project to be added."""
        self.new_project = value

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
            
    def add_project(self, key_event=None):
        """Add a new project to the projects list.
        
        Args:
            key_event: The keyboard event, if triggered by a key press.
        """
        # Only proceed if it's not a key event or if the key is Enter
        if key_event is None or key_event.key == "Enter":
            if self.new_project and self.new_project not in self.projects:
                self.projects.append(self.new_project)
                self.new_project = ""

    def remove_project(self, project: str):
        """Remove a project from the projects list."""
        if project in self.projects:
            self.projects.remove(project)

    @rx.var
    def has_about(self) -> bool:
        """Check if about text exists."""
        return len(self.about) > 0

    async def load_profile_data(self):
        """Load profile data based on the username from the URL."""
        if self.profile_username:
            try:
                # Make API call to fetch user profile data
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://127.0.0.1:8000/api/auth/profile/{self.profile_username}",
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        print(f"Received user data: {user_data}")  # Debug print
                        
                        # Update basic info
                        self.first_name = user_data.get("first_name", "")
                        self.last_name = user_data.get("last_name", "")
                        self.name = f"{self.first_name} {self.last_name}"
                        self.job_title = user_data.get("job_title", "")
                        self.experience_level = user_data.get("experience_level", "")
                        self.category = user_data.get("category", "")
                        self.about = user_data.get("about", "")
                        
                        # Handle skills
                        skills_data = user_data.get("skills", [])
                        if isinstance(skills_data, list):
                            self.skills = skills_data
                        elif isinstance(skills_data, str):
                            # Handle case where skills might be a comma-separated string
                            self.skills = [s.strip() for s in skills_data.split(",") if s.strip()]
                        
                        # Handle projects
                        projects_data = user_data.get("projects", [])
                        if isinstance(projects_data, list):
                            self.projects = projects_data
                        elif isinstance(projects_data, str):
                            # Handle case where projects might be a comma-separated string
                            self.projects = [p.strip() for p in projects_data.split(",") if p.strip()]
                            
                        # Handle social links
                        self.linkedin_link = user_data.get("linkedin_link", "")
                        self.github_link = user_data.get("github_link", "")
                        self.portfolio_link = user_data.get("portfolio_link", "")
                        
                        # Handle profile picture if available
                        if "profile_picture" in user_data:
                            AuthState.profile_picture = user_data["profile_picture"]
                    else:
                        print(f"Error fetching profile data: {response.status_code}")
                        print(f"Response: {response.text}")
                        # Use demo data as fallback
                        self.name = f"Profile of {self.profile_username}"
                        
            except Exception as e:
                print(f"Error in load_profile_data: {str(e)}")
                # Use demo data as fallback
                self.name = f"Profile of {self.profile_username}"

def skill_badge(skill: str) -> rx.Component:
    """Create a badge for a skill."""
    return rx.badge(
        skill,
        class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-lg m-1"
    )

def project_badge(project: str) -> rx.Component:
    """Create a badge for a project."""
    return rx.badge(
        project,
        class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-lg m-1"
    )

def profile_display() -> rx.Component:
    """Render the profile display component."""
    return rx.box(
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
                    rx.heading(State.name, size="7", class_name="text-sky-600 font-bold"),
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
                    rx.icon("pencil"),  # This is the pencil icon
                    on_click=State.toggle_edit_form,
                    class_name="px-6 py-3 bg-white text-gray-600 rounded-lg hover:bg-sky-200 hover:text-gray-600 transition-all duration-200"),
                width="100%",
                padding="4",
                spacing="4"
            ),
            
            # About Section
            rx.box(
                rx.heading("About", size="5", margin_bottom="2"),
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
                rx.hstack(
                    rx.heading("Skills", size="5"),
                    rx.spacer(),
                    width="100%",
                    margin_bottom="2",
                ),
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
            
            # Projects Section
            rx.box(
                rx.hstack(
                    rx.heading("Projects", size="5"),
                    rx.spacer(),
                    width="100%",
                    margin_bottom="2",
                ),
                rx.cond(
                    State.projects.length() > 0,
                    rx.flex(
                        rx.foreach(
                            State.projects,
                            project_badge
                        ),
                        wrap="wrap",
                        gap="2"
                    ),
                    rx.text("No projects added yet.", class_name="text-gray-500 italic")
                ),
                width="100%",
                padding="4",
                class_name="bg-white rounded-lg shadow"
            ),
            
            # Online Presence Section
            rx.box(
                rx.heading("Online Presence", size="5", margin_bottom="2"),
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
            max_width="1000px",
            margin="auto",
            padding="4",
            spacing="4"
        ),
        class_name="bg-white rounded-lg shadow-lg p-6 w-full max-w-6xl mx-auto"
    )

def edit_form() -> rx.Component:
    """Render the edit form as a modal dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Edit Profile", 
                class_name="text-3xl font-bold mb-4 text-blue-600",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
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
                                        border_radius="full",
                                    ),
                                    rx.center(
                                        rx.icon("image", color="gray", size=24),
                                        width="100%",
                                        height="100%",
                                        border_radius="full"
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
                                class_name="px-4 py-2 bg-gray-200 text-gray-700 hover:bg-gray-300 rounded-lg mt-2",
                            ),
                            align="center",
                            spacing="2",
                            margin_bottom="6"
                        ),
                        
                        # Name Fields
                        rx.hstack(
                            rx.vstack(
                                rx.text("First Name", font_weight="medium", align="left", width="100%"),
                                rx.input(
                                    placeholder="First Name",
                                    name="first_name",
                                    required=True,
                                    value=State.first_name,
                                    on_change=State.set_first_name,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            rx.vstack(
                                rx.text("Last Name", font_weight="medium", align="left", width="100%"),
                                rx.input(
                                    placeholder="Last Name",
                                    name="last_name",
                                    required=True,
                                    value=State.last_name,
                                    on_change=State.set_last_name,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            width="100%",
                            spacing="4"
                        ),
                        
                        # Job Title Field
                        rx.text("Job Title", font_weight="medium", align="left", width="100%"),
                        rx.input(
                            placeholder="Your job title",
                            name="job_title",
                            value=State.job_title,
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        
                        # Industry & Experience
                        rx.hstack(
                            rx.vstack(
                                rx.text("Industry", font_weight="medium", align="left", width="100%"),
                                rx.select(
                                    ["Technology", "Finance", "Healthcare", "Education", "E-commerce", "Other"],
                                    placeholder="Select industry",
                                    name="category",
                                    value=State.category,
                                    on_change=State.set_category,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            rx.vstack(
                                rx.text("Years of Experience", font_weight="medium", align="left", width="100%"),
                                rx.select(
                                    ["< 1 year", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
                                    placeholder="Select experience",
                                    name="experience_level",
                                    value=State.experience_level,
                                    on_change=State.set_experience_level,
                                    class_name="w-full p-2 border rounded-lg bg-white",
                                ),
                                width="100%",
                                align_items="start"
                            ),
                            width="100%",
                            spacing="4"
                        ),
                        
                        # About Section
                        rx.text("About", font_weight="medium", align="left", width="100%"),
                        rx.text_area(
                            placeholder="Tell us about yourself...",
                            name="about",
                            value=State.about,
                            on_change=State.set_about,
                            height="120px",
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        
                        # Skills Section
                        rx.text("Skills", font_weight="medium", align="left", width="100%", margin_top="4"),
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
                                    class_name="bg-blue-100 text-blue-700 px-3 py-1 rounded-full m-1",
                                )
                            ),
                            wrap="wrap",
                            margin_bottom="2",
                        ),
                        rx.hstack(
                            rx.input(
                                placeholder="Add more skills...",
                                name="new_skill",
                                value=State.new_skill,
                                on_change=State.set_new_skill,
                                on_key_down=State.add_skill,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            rx.button(
                                "Add",
                                on_click=State.add_skill,
                                class_name="bg-sky-600 text-white px-4 py-1 ml-2 rounded-lg",
                            ),
                            width="100%",
                        ),
                        
                        # Projects Section
                        rx.text("Projects", font_weight="medium", align="left", width="100%", margin_top="4"),
                        rx.flex(
                            rx.foreach(
                                State.projects,
                                lambda project: rx.hstack(
                                    rx.text(project),
                                    rx.icon(
                                        "x",
                                        cursor="pointer",
                                        on_click=lambda p=project: State.remove_project(p),
                                        color="gray",
                                        size=16
                                    ),
                                    class_name="bg-green-100 text-green-700 px-3 py-1 rounded-full m-1",
                                )
                            ),
                            wrap="wrap",
                            margin_bottom="2",
                        ),
                        rx.hstack(
                            rx.input(
                                placeholder="Add project...",
                                name="new_project",
                                value=State.new_project,
                                on_change=State.set_new_project,
                                on_key_down=State.add_project,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            rx.button(
                                "Add",
                                on_click=State.add_project,
                                class_name="bg-sky-600 text-white px-4 py-1 ml-2 rounded-lg",
                            ),
                            width="100%",
                        ),
                        
                        # Online Presence
                        rx.text("Online Presence", font_weight="medium", align="left", width="100%", margin_top="4"),
                        rx.hstack(
                            rx.icon("linkedin", color="blue.500"),
                            rx.input(
                                placeholder="LinkedIn URL",
                                name="linkedin_link",
                                value=State.linkedin_link,
                                on_change=State.set_linkedin_link,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            width="100%"
                        ),
                        rx.hstack(
                            rx.icon("github", color="gray.800"),
                            rx.input(
                                placeholder="GitHub URL",
                                name="github_link",
                                value=State.github_link,
                                on_change=State.set_github_link,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            width="100%"
                        ),
                        rx.hstack(
                            rx.icon("globe", color="green.500"),
                            rx.input(
                                placeholder="Portfolio Website",
                                name="portfolio_link",
                                value=State.portfolio_link,
                                on_change=State.set_portfolio_link,
                                class_name="w-full p-2 border rounded-lg bg-white",
                            ),
                            width="100%"
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.dialog.close(
                                rx.button(
                                    "Cancel",
                                    class_name="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg",
                                ),
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Profile",
                                    type="submit",
                                    class_name="px-6 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="6",
                        ),
                        spacing="6",
                        padding="4",
                    ),
                    on_submit=State.save_changes,
                    reset_on_submit=False,
                ),
                width="100%",
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=State.show_edit_form,
    )

@rx.page(route="/profile/[profile_name]")
def profile_page() -> rx.Component:
    """Render the profile page."""
    return rx.box(
        rx.center(
            rx.cond(
                State.get_username != "",
                # Profile loaded successfully
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            State.name,
                            size="4",
                            color="white",
                            class_name="mb-4"
                        ),
                        rx.spacer(),
                        width="100%",
                    ),
                    # Profile content
                    profile_display(),
                    # Edit form modal
                    edit_form(),
                    width="100%",
                    padding="4",
                ),
                # Loading or error state
                rx.vstack(
                    rx.heading(
                        "Loading profile...",
                        size="4",
                        color="white",
                        class_name="mb-4"
                    ),
                    rx.spinner(
                        color="white",
                        size="3",
                        thickness=4,
                    ),
                    padding="8",
                ),
            ),
            width="100%",
            padding="4",
            height="100vh"
        ),
        on_mount=State.on_mount,
        class_name="min-h-screen bg-gray-900 py-8 items-center justify-center"
    )

@rx.page(route="/profile")
def base_profile_page() -> rx.Component:
    """Render the base profile page."""
    return rx.box(
        rx.center(
            rx.vstack(
                rx.heading("Please provide a username", size="4", color="white"),
                rx.button(
                    "Go Home",
                    on_click=rx.redirect("/"),
                    class_name="bg-sky-600 text-white px-6 py-2 rounded-lg"
                ),
                padding="8",
            ),
            width="100%",
            padding="4",
            height="100vh"
        ),
        class_name="min-h-screen bg-gray-900 py-8 items-center justify-center"
    )