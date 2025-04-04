import reflex as rx
import httpx
from typing import List, Optional
from ..Auth.AuthPage import AuthState

class Project(rx.Base):
    """A project model."""
    id: Optional[int]
    name: str
    description: str
    tech_stack: List[str] = []  # Changed from skills to tech_stack
    funding_stage: str = "Pre-seed"
    team_size: int = 1
    looking_for: List[str] = []

class MyProjectsState(rx.State):
    """The state for the my projects page."""
    
    # API endpoint - base URL
    API_URL = "http://startup-hub:8000/api"  # Changed to base URL
    
    # Projects list
    projects: List[Project] = []
    
    # Modal states
    show_modal: bool = False
    show_edit_modal: bool = False
    editing_project: Optional[Project] = None
    
    # Error handling
    error: Optional[str] = None
    
    @rx.var
    def has_projects(self) -> bool:
        """Check if there are any projects."""
        return len(self.projects) > 0
    
    @rx.var
    def formatted_tech_stack(self) -> str:
        """Get tech stack as comma-separated string."""
        if self.editing_project and self.editing_project.tech_stack:
            return ",".join(self.editing_project.tech_stack)
        return ""
    
    @rx.var
    def formatted_looking_for(self) -> str:
        """Get looking for roles as comma-separated string."""
        if self.editing_project and self.editing_project.looking_for:
            return ",".join(self.editing_project.looking_for)
        return ""
    
    @rx.var
    def formatted_team_size(self) -> str:
        """Get team size as string."""
        if self.editing_project:
            return str(self.editing_project.team_size)
        return "1"

    async def on_mount(self):
        """Load projects when the component mounts."""
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
                else:
                    return rx.redirect("/login")

            # Get username from auth debug
            auth_debug_data = await self.debug_auth_token(auth_token)
            username = auth_debug_data.get("user_from_token", {}).get("username")
            if not username:
                self.error = "Could not determine username"
                return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                # Use the correct endpoint with username filter
                response = await client.get(
                    f"{self.API_URL}/startup-profile/startup-ideas/?username={username}",
                    headers=headers
                )
                
                print(f"Load projects response: {response.status_code}")  # Debug print
                print(f"Response content: {response.text}")  # Debug print
                
                if response.status_code == 200:
                    data = response.json()
                    # Handle both list and paginated response formats
                    results = data.get("results", []) if isinstance(data, dict) else data
                    # Filter projects by username on the client side as well
                    filtered_results = [item for item in results if item.get("username") == username]
                    self.projects = [
                        Project(
                            id=item.get("id"),
                            name=item.get("name", ""),
                            description=item.get("description", ""),
                            tech_stack=item.get("skills_list", []),  # Use skills_list from API
                            funding_stage=item.get("funding_stage", "Pre-seed"),
                            team_size=item.get("member_count", 1),
                            looking_for=item.get("looking_for_list", [])  # Use looking_for_list from API
                        )
                        for item in filtered_results
                    ]
                elif response.status_code == 401:
                    return rx.redirect("/login")
                else:
                    self.error = f"Failed to load projects: {response.text}"
                    print(f"Error loading projects: {response.text}")
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in load_projects: {str(e)}")
    
    def toggle_modal(self):
        """Toggle the create project modal."""
        self.show_modal = not self.show_modal
        if not self.show_modal:
            self.error = None  # Clear any previous errors when closing modal
    
    def toggle_edit_modal(self):
        """Toggle the edit project modal."""
        self.show_edit_modal = not self.show_edit_modal
        if not self.show_edit_modal:
            self.editing_project = None
            self.error = None  # Clear any previous errors when closing modal
    
    def start_edit(self, project: Project):
        """Start editing a project."""
        self.editing_project = project
        self.show_edit_modal = True
    
    async def create_project(self, form_data: dict):
        """Create a new project."""
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                # Get token from localStorage without using await
                token = rx.call_script("localStorage.getItem('auth_token')")
                if token and not hasattr(token, 'event_spec'):
                    auth_token = token
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            # Get username from auth debug
            auth_debug_data = await self.debug_auth_token(auth_token)
            username = auth_debug_data.get("user_from_token", {}).get("username")
            if not username:
                self.error = "Could not determine username"
                return
            
            # Clean and prepare the data
            tech_stack = form_data.get("tech_stack", "").strip()
            looking_for = form_data.get("looking_for", "").strip()
            
            # Prepare project data with proper data types
            project_data = {
                "name": form_data.get("name", "").strip() or "Untitled Project",
                "stage": "IDEA",
                "user_role": "FOUNDER",
                "pitch": form_data.get("description", "").strip() or "No pitch provided",
                "description": form_data.get("description", "").strip() or "No description provided",
                "skills": tech_stack,  # Send as string, let backend handle parsing
                "looking_for": looking_for,  # Send as string, let backend handle parsing
                "pitch_deck": "https://example.com/pitch-deck",  # Valid URL
                "website": "https://example.com",  # Valid URL
                "funding_stage": form_data.get("funding_stage") or "Pre-seed",
                "investment_needed": 0,  # Integer
                "team_size": int(form_data.get("team_size", 1)) if form_data.get("team_size") else 1  # Integer
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            print(f"Sending project data: {project_data}")
            
            async with httpx.AsyncClient() as client:
                # Create the project using POST with JSON data
                response = await client.post(
                    f"{self.API_URL}/startup-profile/startup-ideas/",
                    json=project_data,
                    headers=headers
                )
                
                print(f"Create project response: {response.status_code}")  # Debug print
                print(f"Response content: {response.text}")  # Debug print
                
                if response.status_code in [200, 201]:
                    self.show_modal = False
                    await self.load_projects()  # Reload projects to show the new one
                else:
                    self.error = f"Failed to create project: {response.text}"
                    print(f"Error creating project: {response.text}")  # Debug print
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in create_project: {str(e)}")  # Debug print
    
    async def edit_project(self, form_data: dict):
        """Edit an existing project."""
        if not self.editing_project:
            return
            
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            # Get username from auth debug
            auth_debug_data = await self.debug_auth_token(auth_token)
            username = auth_debug_data.get("user_from_token", {}).get("username")
            if not username:
                self.error = "Could not determine username"
                return
            
            # Validate required fields
            if not form_data.get("name", "").strip():
                self.error = "Project name is required"
                return
                
            if not form_data.get("description", "").strip():
                self.error = "Project description is required"
                return
            
            # Clean and prepare the data
            tech_stack = [tech.strip() for tech in form_data.get("tech_stack", "").split(",") if tech.strip()]
            looking_for = [role.strip() for role in form_data.get("looking_for", "").split(",") if role.strip()]
            
            # Convert team size to integer with validation
            try:
                team_size = int(form_data.get("team_size", 1))
                if team_size < 1:
                    team_size = 1
            except (ValueError, TypeError):
                team_size = 1
            
            # Prepare project data with proper NULL handling and formatting
            project_data = {
                "name": form_data.get("name", "").strip(),
                "stage": "IDEA",  # Default value
                "user_role": "FOUNDER",  # Default value
                "pitch": form_data.get("description", "").strip(),  # Use description as pitch
                "description": form_data.get("description", "").strip(),
                "skills": ",".join(tech_stack) if tech_stack else "",  # Convert list to comma-separated string
                "looking_for": ",".join(looking_for) if looking_for else "",  # Convert list to comma-separated string
                "pitch_deck": "",  # Empty string instead of None
                "website": "",  # Empty string instead of None
                "funding_stage": form_data.get("funding_stage") or "Pre-seed",
                "investment_needed": 0,  # Default value
                "team_size": team_size
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            print(f"Sending update data: {project_data}")  # Debug print
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.API_URL}/startup-profile/startup-ideas/{self.editing_project.id}/",  # Include project ID
                    json=project_data,
                    headers=headers
                )
                
                print(f"Update project response: {response.status_code}")  # Debug print
                print(f"Response content: {response.text}")  # Debug print
                
                if response.status_code == 200:
                    self.show_edit_modal = False
                    self.editing_project = None
                    self.error = None  # Clear any errors
                    await self.load_projects()  # Reload projects to show the changes
                elif response.status_code == 401:
                    return rx.redirect("/login")
                else:
                    self.error = f"Failed to update project: {response.text}"
                    print(f"Error updating project: {response.text}")  # Debug print
                    
        except Exception as e:
            self.error = f"An error occurred while updating the project: {str(e)}"
            print(f"Exception in edit_project: {str(e)}")  # Debug print
    
    async def delete_project(self, project_name: str):
        """Delete a project."""
        try:
            # Find the project by name
            project = next((p for p in self.projects if p.name == project_name), None)
            if not project:
                return
            
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            # Get username from auth debug
            auth_debug_data = await self.debug_auth_token(auth_token)
            username = auth_debug_data.get("user_from_token", {}).get("username")
            if not username:
                self.error = "Could not determine username"
                return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.API_URL}/startup-profile/startup-ideas/{project.id}/",  # Include project ID
                    headers=headers
                )
                
                if response.status_code == 204:
                    await self.load_projects()  # Reload projects after deletion
                else:
                    self.error = f"Failed to delete project: {response.text}"
                    print(f"Error deleting project: {response.text}")  # Debug print
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in delete_project: {str(e)}")  # Debug print

    async def debug_auth_token(self, token: str):
        """Debug authentication token validity using the auth-debug endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://startup-hub:8000/api/auth/auth-debug/",
                    headers={
                        "Authorization": f"Token {token}",
                        "Accept": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                return {}
        except Exception as e:
            print(f"Error in debug_auth_token: {e}")
            return {}