import reflex as rx
import httpx
from typing import List, Optional
from dataclasses import dataclass, field
from Startup_HUB.Search.auth import AuthState  # Update the import path

@dataclass
class Project:
    name: str
    description: str
    pitch: str = ""
    stage: str = "IDEA"
    user_role: str = "FOUNDER"
    tech_stack: List[str] = field(default_factory=list)
    funding_stage: str = "Pre-seed"
    team_size: int = 1
    looking_for: List[str] = field(default_factory=list)
    website: str = ""
    investment_needed: Optional[float] = None
    pitch_deck: str = ""  # Added pitch_deck field

    def get_full_name(self) -> str:
        """Get the full name of the project."""
        return self.name

class MyProjectsState(rx.State):
    """State for managing user's projects."""
    
    # API configuration
    API_BASE_URL: str = "http://100.95.107.24:8000/api/startup-profile/startup-ideas"
    
    # State variables
    projects: List[Project] = []
    show_modal: bool = False
    show_edit_modal: bool = False
    editing_project: Optional[Project] = None
    error_message: Optional[str] = None
    is_loading: bool = False
    auth_token: str = ""  # Add token state variable

    @rx.var
    def has_projects(self) -> bool:
        """Check if there are any projects."""
        return len(self.projects) > 0
        
    @rx.var
    def formatted_tech_stack(self) -> str:
        """Get the formatted tech stack for the editing project."""
        if self.editing_project:
            return ",".join(self.editing_project.tech_stack)
        return ""
        
    @rx.var
    def formatted_looking_for(self) -> str:
        """Get the formatted looking_for for the editing project."""
        if self.editing_project:
            return ",".join(self.editing_project.looking_for)
        return ""
        
    @rx.var
    def formatted_team_size(self) -> str:
        """Get the formatted team size for the editing project."""
        if self.editing_project:
            return str(self.editing_project.team_size)
        return "1"

    def handle_auth_error(self):
        """Handle authentication errors by redirecting to login."""
        self.error_message = "Authentication error. Please log in again."
        return rx.redirect("/login")

    async def on_mount(self):
        """Load projects when the page mounts."""
        # Get token from AuthState first
        auth_state = await self.get_state(AuthState)
        auth_token = auth_state.token
        
        # If token is not in AuthState, try to get it from localStorage
        if not auth_token:
            auth_token = await rx.get_client_storage("auth_token")
            if auth_token:
                auth_state.set_token(auth_token)
                print(f"Token initialized from client storage: {auth_token}")
            else:
                print("No token found in client storage")
                return self.handle_auth_error()
        
        # Load projects
        return self.load_projects()

    @rx.event
    async def load_projects(self):
        """Load projects from the API."""
        try:
            # Get token from AuthState first
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            # If token is not in AuthState, try to get it from localStorage
            if not auth_token:
                auth_token = await rx.get_client_storage("auth_token")
                if auth_token:
                    auth_state.set_token(auth_token)
            
            # If token is empty, redirect to login
            if not auth_token:
                return self.handle_auth_error()
            
            print(f"Token for loading projects: {auth_token}")
            
            # Use httpx to make the request directly from the server
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Token {auth_token}"
                    }
                )
                
                print(f"Projects loading response: {response.status_code}")
                
                if response.status_code == 200:
                    # Projects loaded successfully
                    print("Projects loaded successfully")
                    projects_data = response.json()
                    
                    # Convert API response to Project objects
                    self.projects = []
                    for project_data in projects_data:
                        project = Project(
                            name=project_data.get("name", ""),
                            description=project_data.get("description", ""),
                            pitch=project_data.get("pitch", ""),
                            stage=project_data.get("stage", "IDEA"),
                            user_role=project_data.get("user_role", "FOUNDER"),
                            tech_stack=project_data.get("tech_stack", []),
                            funding_stage=project_data.get("funding_stage", "Pre-seed"),
                            team_size=project_data.get("team_size", 1),
                            looking_for=project_data.get("looking_for", []),
                            website=project_data.get("website", ""),
                            investment_needed=project_data.get("investment_needed"),
                            pitch_deck=project_data.get("pitch_deck", "")
                        )
                        self.projects.append(project)
                elif response.status_code == 401:
                    # Authentication error
                    print("Authentication error when loading projects")
                    return self.handle_auth_error()
                else:
                    # Other error
                    error_data = response.json() if response.status_code >= 400 else {}
                    error_message = error_data.get("detail", "Unknown error")
                    self.error_message = f"Error loading projects: {error_message}"
                    print(f"Error loading projects: {error_message}")
        except Exception as e:
            print(f"Error in load_projects: {e}")
            self.error_message = f"Error loading projects: {str(e)}"

    def toggle_modal(self):
        """Toggle the create project modal."""
        self.show_modal = not self.show_modal
        if not self.show_modal:
            self.error_message = None

    def toggle_edit_modal(self):
        """Toggle the edit project modal."""
        self.show_edit_modal = not self.show_edit_modal
        if not self.show_edit_modal:
            self.error_message = None
            self.editing_project = None

    def start_edit(self, project: Project):
        """Start editing a project."""
        self.editing_project = project
        self.show_edit_modal = True

    @rx.event
    async def refresh_token(self):
        """Refresh the auth token."""
        # Get token from AuthState first
        auth_state = await self.get_state(AuthState)
        auth_token = auth_state.token
        
        # If token is not in AuthState, try to get it from localStorage
        if not auth_token:
            auth_token = await rx.get_client_storage("auth_token")
            if auth_token:
                auth_state.set_token(auth_token)
                print(f"Token refreshed from client storage: {auth_token}")
        
        print(f"Token refreshed: {auth_token}")
        return auth_token

    @rx.event
    async def edit_project(self, form_data: dict):
        """Edit an existing project."""
        try:
            # Get token using the refresh_token method
            auth_token = await self.refresh_token()
            
            # If token is empty, redirect to login
            if not auth_token:
                return self.handle_auth_error()
            
            print(f"Token for project edit: {auth_token}")
            
            # Create a new Project instance with the updated data
            updated_project = Project(
                name=form_data.get("name", ""),
                description=form_data.get("description", ""),
                pitch=form_data.get("pitch", ""),
                stage=form_data.get("stage", "IDEA"),
                user_role=form_data.get("user_role", "FOUNDER"),
                tech_stack=form_data.get("tech_stack", "").split(",") if form_data.get("tech_stack") else [],
                funding_stage=form_data.get("funding_stage", "Pre-seed"),
                team_size=int(form_data.get("team_size", 1)),
                looking_for=form_data.get("looking_for", "").split(",") if form_data.get("looking_for") else [],
                website=form_data.get("website", ""),
                investment_needed=float(form_data.get("investment_needed", 0)) if form_data.get("investment_needed") else None,
                pitch_deck=form_data.get("pitch_deck", "")
            )
            
            # Prepare project data for API
            project_data = {
                "name": updated_project.name,
                "description": updated_project.description,
                "pitch": updated_project.pitch,
                "stage": updated_project.stage,
                "user_role": updated_project.user_role,
                "tech_stack": updated_project.tech_stack,
                "funding_stage": updated_project.funding_stage,
                "team_size": updated_project.team_size,
                "looking_for": updated_project.looking_for,
                "website": updated_project.website,
                "investment_needed": updated_project.investment_needed,
                "pitch_deck": updated_project.pitch_deck
            }
            
            # Remove None values
            project_data = {k: v for k, v in project_data.items() if v is not None}
            
            print(f"Updating project with data: {project_data}")
            
            # Use httpx to make the request directly from the server
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.API_BASE_URL}/{self.editing_project.name}/",
                    json=project_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Token {auth_token}"
                    }
                )
                
                print(f"Project update response: {response.status_code}")
                
                if response.status_code == 200:
                    # Project updated successfully
                    print("Project updated successfully")
                    # Update the project in the local state
                    for i, project in enumerate(self.projects):
                        if project.name == self.editing_project.name:
                            self.projects[i] = updated_project
                            break
                    # Close the modal
                    self.show_edit_modal = False
                elif response.status_code == 401:
                    # Authentication error
                    print("Authentication error when updating project")
                    return self.handle_auth_error()
                else:
                    # Other error
                    error_data = response.json() if response.status_code >= 400 else {}
                    error_message = error_data.get("detail", "Unknown error")
                    if isinstance(error_message, dict):
                        # Format validation errors
                        formatted_errors = []
                        for field, errors in error_message.items():
                            if isinstance(errors, list):
                                formatted_errors.append(f"{field}: {', '.join(errors)}")
                            else:
                                formatted_errors.append(f"{field}: {errors}")
                        error_message = "; ".join(formatted_errors)
                    self.error_message = f"Error updating project: {error_message}"
                    print(f"Error updating project: {error_message}")
        except Exception as e:
            print(f"Error in edit_project: {e}")
            self.error_message = f"Error updating project: {str(e)}"

    @rx.event
    async def create_project(self, form_data: dict):
        """Create a new project."""
        try:
            # Get token using the refresh_token method
            auth_token = await self.refresh_token()
            
            # If token is empty, redirect to login
            if not auth_token:
                return self.handle_auth_error()
            
            print(f"Token for project creation: {auth_token}")
            
            # Create a new Project instance to ensure get_full_name method is available
            new_project = Project(
                name=form_data.get("name", ""),
                description=form_data.get("description", ""),
                pitch=form_data.get("pitch", ""),
                stage=form_data.get("stage", "IDEA"),
                user_role=form_data.get("user_role", "FOUNDER"),
                tech_stack=form_data.get("tech_stack", "").split(",") if form_data.get("tech_stack") else [],
                funding_stage=form_data.get("funding_stage", "Pre-seed"),
                team_size=int(form_data.get("team_size", 1)),
                looking_for=form_data.get("looking_for", "").split(",") if form_data.get("looking_for") else [],
                website=form_data.get("website", ""),
                investment_needed=float(form_data.get("investment_needed", 0)) if form_data.get("investment_needed") else None,
                pitch_deck=form_data.get("pitch_deck", "")
            )
            
            # Prepare project data for API
            project_data = {
                "name": new_project.name,
                "description": new_project.description,
                "pitch": new_project.pitch,
                "stage": new_project.stage,
                "user_role": new_project.user_role,
                "tech_stack": new_project.tech_stack,
                "funding_stage": new_project.funding_stage,
                "team_size": new_project.team_size,
                "looking_for": new_project.looking_for,
                "website": new_project.website,
                "investment_needed": new_project.investment_needed,
                "pitch_deck": new_project.pitch_deck
            }
            
            # Remove None values
            project_data = {k: v for k, v in project_data.items() if v is not None}
            
            print(f"Creating project with data: {project_data}")
            
            # Use httpx to make the request directly from the server
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/",
                    json=project_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Token {auth_token}"
                    }
                )
                
                print(f"Project creation response: {response.status_code}")
                
                if response.status_code == 201:
                    # Project created successfully
                    print("Project created successfully")
                    # Add the new project to the local state
                    self.projects.append(new_project)
                    # Close the modal
                    self.show_modal = False
                elif response.status_code == 401:
                    # Authentication error
                    print("Authentication error when creating project")
                    return self.handle_auth_error()
                else:
                    # Other error
                    error_data = response.json() if response.status_code >= 400 else {}
                    error_message = error_data.get("detail", "Unknown error")
                    if isinstance(error_message, dict):
                        # Format validation errors
                        formatted_errors = []
                        for field, errors in error_message.items():
                            if isinstance(errors, list):
                                formatted_errors.append(f"{field}: {', '.join(errors)}")
                            else:
                                formatted_errors.append(f"{field}: {errors}")
                        error_message = "; ".join(formatted_errors)
                    self.error_message = f"Error creating project: {error_message}"
                    print(f"Error creating project: {error_message}")
        except Exception as e:
            print(f"Error in create_project: {e}")
            self.error_message = f"Error creating project: {str(e)}"

    @rx.event
    async def delete_project(self, project_name: str):
        """Delete a project."""
        try:
            # Get token using the refresh_token method
            auth_token = await self.refresh_token()
            
            # If token is empty, redirect to login
            if not auth_token:
                return self.handle_auth_error()
            
            print(f"Token for project deletion: {auth_token}")
            
            # Use httpx to make the request directly from the server
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.API_BASE_URL}/{project_name}/",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Token {auth_token}"
                    }
                )
                
                print(f"Project deletion response: {response.status_code}")
                
                if response.status_code == 204:
                    # Project deleted successfully
                    print("Project deleted successfully")
                    # Remove the project from the local state
                    self.projects = [p for p in self.projects if p.name != project_name]
                elif response.status_code == 401:
                    # Authentication error
                    print("Authentication error when deleting project")
                    return self.handle_auth_error()
                else:
                    # Other error
                    error_data = response.json() if response.status_code >= 400 else {}
                    error_message = error_data.get("detail", "Unknown error")
                    self.error_message = f"Error deleting project: {error_message}"
                    print(f"Error deleting project: {error_message}")
        except Exception as e:
            print(f"Error in delete_project: {e}")
            self.error_message = f"Error deleting project: {str(e)}"