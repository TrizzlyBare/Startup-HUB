import reflex as rx
from typing import List, Optional
from ..Auth.AuthState import AuthState
import httpx

class Project(rx.Base):
    """Project model."""
    id: Optional[int] = None
    name: str
    description: str
    pitch: str
    stage: str
    user_role: str
    tech_stack: List[str]
    team_size: int
    looking_for: List[str]
    website: str
    pitch_deck: str
    funding_stage: str
    investment_needed: float
    username: str

class ProjectsState(rx.State):
    """State for the projects page."""
    
    # API endpoint
    API_URL = "http://100.95.107.24:8000/api/startup-profile/startup-ideas"
    
    # Projects list
    projects: List[Project] = []
    show_modal: bool = False
    show_edit_modal: bool = False
    editing_project: Optional[Project] = None
    error_message: str = ""
    profile_username: str = ""
    
    @rx.var
    def has_projects(self) -> bool:
        """Check if user has any projects."""
        return len(self.projects) > 0
    
    async def on_mount(self):
        """Load projects when the page mounts."""
        # Get username from route parameters
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            self.profile_username = params.get("profile_username", "")
            if not self.profile_username:
                # If no username in URL, get it from auth state
                auth_state = await self.get_state(AuthState)
                if auth_state.token:
                    try:
                        auth_debug_data = await self.debug_auth_token(auth_state.token)
                        user_data = auth_debug_data.get("user_from_token", {})
                        if user_data and "username" in user_data:
                            self.profile_username = user_data["username"]
                            # Redirect to the correct URL with username
                            return rx.redirect(f"/projects/{self.profile_username}")
                    except Exception as e:
                        print(f"Error getting username from auth: {e}")
        
        await self.load_projects()
    
    async def load_projects(self):
        """Load projects from the API."""
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/my-ideas/?username={self.profile_username}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.projects = [
                        Project(
                            id=item.get("id"),
                            name=item.get("name", ""),
                            description=item.get("description", ""),
                            pitch=item.get("pitch", ""),
                            stage=item.get("stage", "IDEA"),
                            user_role=item.get("user_role", "FOUNDER"),
                            tech_stack=item.get("tech_stack", []),
                            team_size=item.get("team_size", 1),
                            looking_for=item.get("looking_for", []),
                            website=item.get("website", ""),
                            pitch_deck=item.get("pitch_deck", ""),
                            funding_stage=item.get("funding_stage", "Pre-seed"),
                            investment_needed=item.get("investment_needed", 0),
                            username=self.profile_username
                        )
                        for item in data
                    ]
                else:
                    self.error_message = f"Error loading projects: {response.text}"
        except Exception as e:
            self.error_message = f"Error loading projects: {str(e)}"
            self.projects = []
    
    async def create_project(self, form_data: dict):
        """Create a new project."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            project_data = {
                "name": form_data.get("name", ""),
                "description": form_data.get("description", ""),
                "pitch": form_data.get("pitch", ""),
                "stage": form_data.get("stage", "IDEA"),
                "user_role": form_data.get("user_role", "FOUNDER"),
                "tech_stack": form_data.get("tech_stack", "").split(","),
                "team_size": int(form_data.get("team_size", 1)),
                "looking_for": form_data.get("looking_for", "").split(","),
                "website": form_data.get("website", ""),
                "pitch_deck": form_data.get("pitch_deck", ""),
                "funding_stage": form_data.get("funding_stage", "Pre-seed"),
                "investment_needed": float(form_data.get("investment_needed", 0)),
                "username": self.profile_username
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/my-ideas/",
                    json=project_data,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    self.show_modal = False
                    await self.load_projects()
                else:
                    self.error_message = f"Error creating project: {response.text}"
        except Exception as e:
            self.error_message = f"Error creating project: {str(e)}"
    
    async def edit_project(self, form_data: dict):
        """Edit an existing project."""
        try:
            if not self.editing_project:
                return
            
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            project_data = {
                "name": form_data.get("name", ""),
                "description": form_data.get("description", ""),
                "pitch": form_data.get("pitch", ""),
                "stage": form_data.get("stage", "IDEA"),
                "user_role": form_data.get("user_role", "FOUNDER"),
                "tech_stack": form_data.get("tech_stack", "").split(","),
                "team_size": int(form_data.get("team_size", 1)),
                "looking_for": form_data.get("looking_for", "").split(","),
                "website": form_data.get("website", ""),
                "pitch_deck": form_data.get("pitch_deck", ""),
                "funding_stage": form_data.get("funding_stage", "Pre-seed"),
                "investment_needed": float(form_data.get("investment_needed", 0)),
                "username": self.profile_username
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.API_URL}/my-ideas/{self.editing_project.id}/",
                    json=project_data,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    self.show_edit_modal = False
                    self.editing_project = None
                    await self.load_projects()
                else:
                    self.error_message = f"Error updating project: {response.text}"
        except Exception as e:
            self.error_message = f"Error updating project: {str(e)}"
    
    async def delete_project(self, project_name: str):
        """Delete a project."""
        try:
            project = next((p for p in self.projects if p.name == project_name), None)
            if not project:
                return
            
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.API_URL}/my-ideas/{project.id}/?username={self.profile_username}",
                    headers=headers
                )
                
                if response.status_code == 204:
                    await self.load_projects()
                else:
                    self.error_message = f"Error deleting project: {response.text}"
        except Exception as e:
            self.error_message = f"Error deleting project: {str(e)}"
    
    def toggle_modal(self):
        """Toggle the create project modal."""
        self.show_modal = not self.show_modal
    
    def toggle_edit_modal(self):
        """Toggle the edit project modal."""
        self.show_edit_modal = not self.show_edit_modal
        if not self.show_edit_modal:
            self.editing_project = None
    
    def start_edit(self, project: Project):
        """Start editing a project."""
        self.editing_project = project
        self.show_edit_modal = True

def project_card(project: Project) -> rx.Component:
    """Create a card for a project."""
    return rx.box(
        rx.vstack(
            # Project header
            rx.heading(project.name, size="6", class_name="text-sky-600 font-bold"),
            rx.text(
                project.description,
                noOfLines=3,
                class_name="text-md font-small text-gray-400",
            ),
            
            # Project details
            rx.vstack(
                # Stage and User Role
                rx.hstack(
                    rx.badge(
                        project.stage,
                        class_name="bg-blue-100 text-blue-800 px-3 py-1 rounded-full"
                    ),
                    rx.badge(
                        project.user_role,
                        class_name="bg-green-100 text-green-800 px-3 py-1 rounded-full"
                    ),
                    spacing="2"
                ),
                
                # Pitch
                rx.box(
                    rx.text("Elevator Pitch:", class_name="text-lg font-medium mt-2"),
                    rx.text(
                        project.pitch,
                        noOfLines=2,
                        class_name="text-md text-gray-600",
                    ),
                ),
                
                # Tech Stack
                rx.box(
                    rx.text("Tech Stack:", class_name="text-lg font-medium mt-2"),
                    rx.flex(
                        rx.foreach(
                            project.tech_stack,
                            lambda tech: rx.badge(
                                tech,
                                class_name="bg-gray-100 text-gray-800 px-3 py-1 rounded-full m-1"
                            )
                        ),
                        wrap="wrap",
                    ),
                ),
                
                # Looking for
                rx.box(
                    rx.text("Looking for:", class_name="text-lg font-medium mt-2"),
                    rx.flex(
                        rx.foreach(
                            project.looking_for,
                            lambda role: rx.badge(
                                role,
                                class_name="bg-purple-100 text-purple-800 px-3 py-1 rounded-full m-1"
                            )
                        ),
                        wrap="wrap",
                    ),
                ),
                
                # Links
                rx.hstack(
                    rx.cond(
                        project.website,
                        rx.link(
                            rx.text("Website", class_name="text-blue-600 hover:underline"),
                            href=project.website,
                            is_external=True,
                        ),
                        rx.text("No website", class_name="text-gray-400"),
                    ),
                    rx.cond(
                        project.pitch_deck,
                        rx.link(
                            rx.text("Pitch Deck", class_name="text-blue-600 hover:underline"),
                            href=project.pitch_deck,
                            is_external=True,
                        ),
                        rx.text("No pitch deck", class_name="text-gray-400"),
                    ),
                    spacing="4",
                ),
                
                # Funding
                rx.box(
                    rx.text(
                        f"Funding Stage: {project.funding_stage}",
                        class_name="text-md font-medium",
                    ),
                    rx.text(
                        f"Investment Needed: ${project.investment_needed:,.2f}",
                        class_name="text-md font-medium",
                    ),
                ),
                
                # Buttons
                rx.hstack(
                    rx.button(
                        rx.icon("pencil"),
                        on_click=lambda: ProjectsState.start_edit(project),
                        class_name="px-4 py-2 bg-white text-gray-600 rounded-lg hover:bg-sky-200 hover:text-gray-600 transition-all duration-200"
                    ),
                    rx.button(
                        rx.icon("trash"),
                        on_click=lambda: ProjectsState.delete_project(project.name),
                        class_name="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-all duration-200"
                    ),
                    spacing="4",
                    justify="end",
                ),
                
                spacing="4",
                width="100%",
            ),
            
            width="100%",
            padding="6",
            class_name="bg-white rounded-lg shadow hover:shadow-lg transition-all duration-200"
        ),
        width="100%",
    )

def create_project_modal() -> rx.Component:
    """Create project modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Create New Project",
                class_name="text-3xl font-bold mb-4 text-blue-600",
            ),
            rx.box(
                rx.form(
                    rx.vstack(
                        # Project name field with label
                        rx.vstack(
                            rx.text("Project Name", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="Enter your project name",
                                name="name",
                                required=True,
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Description field with label
                        rx.vstack(
                            rx.text("Description", class_name="font-medium text-gray-700 mb-1"),
                            rx.text_area(
                                placeholder="Describe your project in detail",
                                name="description",
                                required=True,
                                height="120px",
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Pitch field with label
                        rx.vstack(
                            rx.text("Elevator Pitch", class_name="font-medium text-gray-700 mb-1"),
                            rx.text_area(
                                placeholder="Brief, compelling summary of your project",
                                name="pitch",
                                required=True,
                                height="100px",
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Two columns for stage and role
                        rx.hstack(
                            # Stage field with label
                            rx.vstack(
                                rx.text("Project Stage", class_name="font-medium text-gray-700 mb-1"),
                                rx.select(
                                    ["IDEA", "MVP", "BETA", "LAUNCHED", "SCALING"],
                                    placeholder="Select stage",
                                    name="stage",
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            
                            # Role field with label
                            rx.vstack(
                                rx.text("Your Role", class_name="font-medium text-gray-700 mb-1"),
                                rx.select(
                                    ["FOUNDER", "CO-FOUNDER", "TEAM_MEMBER", "INVESTOR", "ADVISOR"],
                                    placeholder="Select your role",
                                    name="user_role",
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Tech Stack field with label
                        rx.vstack(
                            rx.text("Tech Stack", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="e.g. React, Python, Django (comma-separated)",
                                name="tech_stack",
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Two columns for funding stage and team size
                        rx.hstack(
                            # Funding stage field with label
                            rx.vstack(
                                rx.text("Funding Stage", class_name="font-medium text-gray-700 mb-1"),
                                rx.select(
                                    ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                                    placeholder="Select stage",
                                    name="funding_stage",
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            
                            # Team size field with label
                            rx.vstack(
                                rx.text("Team Size", class_name="font-medium text-gray-700 mb-1"),
                                rx.input(
                                    placeholder="Number of people",
                                    name="team_size",
                                    type="number",
                                    min_value=1,
                                    default_value="1",
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Looking for field with label
                        rx.vstack(
                            rx.text("Looking For", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="e.g. Developer, Designer, Marketing (comma-separated)",
                                name="looking_for",
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Two columns for website and investment
                        rx.hstack(
                            # Website field with label
                            rx.vstack(
                                rx.text("Website URL", class_name="font-medium text-gray-700 mb-1"),
                                rx.input(
                                    placeholder="https://example.com",
                                    name="website",
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            
                            # Investment field with label
                            rx.vstack(
                                rx.text("Investment Needed ($)", class_name="font-medium text-gray-700 mb-1"),
                                rx.input(
                                    placeholder="e.g. 50000",
                                    name="investment_needed",
                                    type="number",
                                    min_value=0,
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Pitch deck field with label
                        rx.vstack(
                            rx.text("Pitch Deck URL", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="Link to your presentation",
                                name="pitch_deck",
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                on_click=ProjectsState.toggle_modal,
                                class_name="px-6 py-3 bg-gray-200 text-gray-800 hover:bg-gray-300 rounded-lg font-medium",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Create Project",
                                    type="submit",
                                    class_name="px-6 py-3 bg-sky-600 text-white hover:bg-sky-700 rounded-lg font-medium",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="8",
                        ),
                        spacing="6",
                        padding="6",
                        bg="white",
                        border_radius="lg",
                    ),
                    on_submit=ProjectsState.create_project,
                    reset_on_submit=True,
                ),
                width="100%",
            ),
            max_width="800px",
            width="90vw",
            class_name="bg-gray-50 p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=ProjectsState.show_modal,
    )

def edit_project_modal() -> rx.Component:
    """Edit project modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Edit Project",
                class_name="text-3xl font-bold mb-4 text-blue-600",
            ),
            rx.box(
                rx.form(
                    rx.vstack(
                        # Project name field with label
                        rx.vstack(
                            rx.text("Project Name", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="Enter your project name",
                                name="name",
                                required=True,
                                default_value=rx.cond(
                                    ProjectsState.editing_project,
                                    ProjectsState.editing_project.name,
                                    ""
                                ),
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Description field with label
                        rx.vstack(
                            rx.text("Description", class_name="font-medium text-gray-700 mb-1"),
                            rx.text_area(
                                placeholder="Describe your project in detail",
                                name="description",
                                required=True,
                                height="120px",
                                default_value=rx.cond(
                                    ProjectsState.editing_project,
                                    ProjectsState.editing_project.description,
                                    ""
                                ),
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Pitch field with label
                        rx.vstack(
                            rx.text("Elevator Pitch", class_name="font-medium text-gray-700 mb-1"),
                            rx.text_area(
                                placeholder="Brief, compelling summary of your project",
                                name="pitch",
                                required=True,
                                height="100px",
                                default_value=rx.cond(
                                    ProjectsState.editing_project,
                                    ProjectsState.editing_project.pitch,
                                    ""
                                ),
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Two columns for stage and role
                        rx.hstack(
                            # Stage field with label
                            rx.vstack(
                                rx.text("Project Stage", class_name="font-medium text-gray-700 mb-1"),
                                rx.select(
                                    ["IDEA", "MVP", "BETA", "LAUNCHED", "SCALING"],
                                    placeholder="Select stage",
                                    name="stage",
                                    default_value=rx.cond(
                                        ProjectsState.editing_project,
                                        ProjectsState.editing_project.stage,
                                        "IDEA"
                                    ),
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            
                            # Role field with label
                            rx.vstack(
                                rx.text("Your Role", class_name="font-medium text-gray-700 mb-1"),
                                rx.select(
                                    ["FOUNDER", "CO-FOUNDER", "TEAM_MEMBER", "INVESTOR", "ADVISOR"],
                                    placeholder="Select your role",
                                    name="user_role",
                                    default_value=rx.cond(
                                        ProjectsState.editing_project,
                                        ProjectsState.editing_project.user_role,
                                        "FOUNDER"
                                    ),
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Tech Stack field with label
                        rx.vstack(
                            rx.text("Tech Stack", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="e.g. React, Python, Django (comma-separated)",
                                name="tech_stack",
                                default_value=rx.cond(
                                    ProjectsState.editing_project,
                                    ",".join(ProjectsState.editing_project.tech_stack),
                                    ""
                                ),
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Two columns for funding stage and team size
                        rx.hstack(
                            # Funding stage field with label
                            rx.vstack(
                                rx.text("Funding Stage", class_name="font-medium text-gray-700 mb-1"),
                                rx.select(
                                    ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                                    placeholder="Select stage",
                                    name="funding_stage",
                                    default_value=rx.cond(
                                        ProjectsState.editing_project,
                                        ProjectsState.editing_project.funding_stage,
                                        "Pre-seed"
                                    ),
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            
                            # Team size field with label
                            rx.vstack(
                                rx.text("Team Size", class_name="font-medium text-gray-700 mb-1"),
                                rx.input(
                                    placeholder="Number of people",
                                    name="team_size",
                                    type="number",
                                    min_value=1,
                                    default_value=rx.cond(
                                        ProjectsState.editing_project,
                                        str(ProjectsState.editing_project.team_size),
                                        "1"
                                    ),
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Looking for field with label
                        rx.vstack(
                            rx.text("Looking For", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="e.g. Developer, Designer, Marketing (comma-separated)",
                                name="looking_for",
                                default_value=rx.cond(
                                    ProjectsState.editing_project,
                                    ",".join(ProjectsState.editing_project.looking_for),
                                    ""
                                ),
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Two columns for website and investment
                        rx.hstack(
                            # Website field with label
                            rx.vstack(
                                rx.text("Website URL", class_name="font-medium text-gray-700 mb-1"),
                                rx.input(
                                    placeholder="https://example.com",
                                    name="website",
                                    default_value=rx.cond(
                                        ProjectsState.editing_project,
                                        ProjectsState.editing_project.website,
                                        ""
                                    ),
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            
                            # Investment field with label
                            rx.vstack(
                                rx.text("Investment Needed ($)", class_name="font-medium text-gray-700 mb-1"),
                                rx.input(
                                    placeholder="e.g. 50000",
                                    name="investment_needed",
                                    type="number",
                                    min_value=0,
                                    default_value=rx.cond(
                                        ProjectsState.editing_project,
                                        str(ProjectsState.editing_project.investment_needed),
                                        "0"
                                    ),
                                    class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                                ),
                                align_items="start",
                                width="100%",
                                spacing="0",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        
                        # Pitch deck field with label
                        rx.vstack(
                            rx.text("Pitch Deck URL", class_name="font-medium text-gray-700 mb-1"),
                            rx.input(
                                placeholder="Link to your presentation",
                                name="pitch_deck",
                                default_value=rx.cond(
                                    ProjectsState.editing_project,
                                    ProjectsState.editing_project.pitch_deck,
                                    ""
                                ),
                                class_name="w-full p-3 border-2 border-gray-300 rounded-lg bg-white focus:border-sky-500 focus:ring-2 focus:ring-sky-200 text-base",
                            ),
                            align_items="start",
                            width="100%",
                            spacing="0",
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                on_click=ProjectsState.toggle_edit_modal,
                                class_name="px-6 py-3 bg-gray-200 text-gray-800 hover:bg-gray-300 rounded-lg font-medium",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Changes",
                                    type="submit",
                                    class_name="px-6 py-3 bg-sky-600 text-white hover:bg-sky-700 rounded-lg font-medium",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="8",
                        ),
                        spacing="6",
                        padding="6",
                        bg="white",
                        border_radius="lg",
                    ),
                    on_submit=ProjectsState.edit_project,
                    reset_on_submit=True,
                ),
                width="100%",
            ),
            max_width="800px",
            width="90vw",
            class_name="bg-gray-50 p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=ProjectsState.show_edit_modal,
    )

def projects_display() -> rx.Component:
    """Render the projects display component."""
    return rx.box(
        rx.vstack(
            # Header section
            rx.box(
                rx.hstack(
                    rx.heading("My Projects", size="9", class_name="text-sky-600 font-bold"),
                    rx.spacer(),
                    rx.button(
                        "+ Create new",
                        on_click=ProjectsState.toggle_modal,
                        class_name="bg-sky-600 text-white hover:bg-sky-500 px-8 py-4 text-xl rounded-lg font-medium"
                    ),
                    width="100%",
                    padding_y="6",
                ),
                border_bottom="1px solid",
                border_color="gray.200",
                width="100%",
                margin_bottom="20",
                padding_x="4",
            ),
            
            # Error message section
            rx.cond(
                ProjectsState.error_message,
                rx.box(
                    rx.text(
                        ProjectsState.error_message,
                        class_name="text-red-500 bg-red-100 p-4 rounded-lg"
                    ),
                    width="100%",
                    padding_x="4",
                    margin_bottom="4",
                ),
            ),
            
            # Projects grid section
            rx.cond(
                ProjectsState.has_projects,
                rx.box(
                    rx.grid(
                        rx.foreach(
                            ProjectsState.projects,
                            project_card
                        ),
                        columns="3",
                        spacing="8",
                        width="100%",
                        padding="8",
                        template_columns="repeat(auto-fit, minmax(450px, 1fr))",
                        gap="8",
                    ),
                    overflow_y="auto",
                    height="calc(100vh - 120px)",
                    padding_x="8",
                    width="100%",
                ),
                rx.vstack(
                    rx.text("You haven't created any projects yet.", class_name="text-white text-lg"),
                    rx.button(
                        "Create Your First Project",
                        on_click=ProjectsState.toggle_modal,
                        class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium mt-4",
                    ),
                    spacing="4",
                    height="calc(100vh - 120px)",
                    align="center",
                    justify="center",
                    width="100%",
                ),
            ),
            
            width="100%",
            height="100vh",
        ),
        create_project_modal(),
        edit_project_modal(),
        class_name="bg-gray-800",
    )

@rx.page(route="/projects/[project_username]")
def projects_page() -> rx.Component:
    """Render the projects page."""
    return rx.box(
        rx.center(
            rx.vstack(
                # Auth check on page load
                rx.script("""
                    // Check token on page load
                    const token = localStorage.getItem('auth_token');
                    if (!token) {
                        console.log('No token found - redirecting to login');
                        window.location.href = '/login';
                    } else {
                        console.log('Token found in localStorage:', token);
                        // Update token display
                        const displayElement = document.getElementById('token-display');
                        if (displayElement) {
                            displayElement.textContent = `Token from localStorage: ${token}`;
                        }
                    }
                """),
                
                # Page content
                rx.hstack(
                    rx.heading(
                        "My Projects",
                        size="4",
                        color="white",
                        class_name="mb-4"
                    ),
                    rx.spacer(),
                    # Add logout button
                    rx.button(
                        "Log Out",
                        on_click=AuthState.logout,
                        class_name="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                    ),
                    width="100%",
                ),
                
                # Projects content
                projects_display(),
                
                width="100%",
                padding="4",
            ),
            width="100%",
            padding="4",
            height="100vh"
        ),
        on_mount=ProjectsState.on_mount,
        class_name="min-h-screen bg-gray-900 py-8 items-center justify-center"
    )

@rx.page(route="/projects")
def base_projects_page() -> rx.Component:
    """Render the base projects page."""
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