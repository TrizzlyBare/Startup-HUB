import reflex as rx
import httpx
from typing import List, Optional, Dict
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

class JoinRequest(rx.Base):
    """A join request model."""
    id: int
    project_name: str
    sender_name: str
    sender_id: int
    status: str
    message: str
    created_at: str

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
    
    # Join request states
    show_join_request_modal: bool = False
    show_join_requests_modal: bool = False
    selected_project: Optional[Project] = None
    join_request_message: str = ""
    join_requests: List[JoinRequest] = []
    
    # Error handling
    error: Optional[str] = None
    
    # Sidebar states
    active_tab: str = "projects"  # Default tab
    matches: List[Dict] = []
    likes: List[Dict] = []
    rooms: List[Dict] = []
    current_chat: Optional[str] = None
    current_group_chat: Optional[str] = None
    current_group_name: Optional[str] = None
    
    def set_active_tab(self, tab: str):
        """Set the active tab in the sidebar."""
        self.active_tab = tab
    
    async def load_matches(self):
        """Load matches from the API."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/matcher/matches/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.matches = response.json()
                elif response.status_code == 401:
                    return rx.redirect("/login")
        except Exception as e:
            print(f"Error loading matches: {str(e)}")
    
    async def load_likes(self):
        """Load likes from the API."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/matcher/likes/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.likes = response.json()
                elif response.status_code == 401:
                    return rx.redirect("/login")
        except Exception as e:
            print(f"Error loading likes: {str(e)}")
    
    async def load_rooms(self):
        """Load chat rooms from the API."""
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/chat/rooms/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    self.rooms = response.json()
                elif response.status_code == 401:
                    return rx.redirect("/login")
        except Exception as e:
            print(f"Error loading rooms: {str(e)}")
    
    def open_chat(self, username: str):
        """Open a chat with a user."""
        self.current_chat = username
        self.current_group_chat = None
        self.current_group_name = None
    
    def open_group_chat(self, room_id: str, room_name: str):
        """Open a group chat."""
        self.current_group_chat = room_id
        self.current_group_name = room_name
        self.current_chat = None
    
    def get_username(self) -> str:
        """Get the current user's username."""
        try:
            # First try to get from AuthState
            auth_state = self.get_state(AuthState)
            if auth_state and hasattr(auth_state, 'username'):
                return auth_state.username
            
            return ""
        except Exception as e:
            print(f"Error getting username: {str(e)}")
            return ""
    
    @rx.var
    def username(self) -> str:
        """Computed var to get the current user's username."""
        return self.get_username()
    
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
        """Load data when the component mounts."""
        await self.load_projects()
        await self.load_matches()
        await self.load_likes()
        await self.load_rooms()
    
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
                "skills_list": [skill.strip() for skill in tech_stack.split(",") if skill.strip()],  # List of skills
                "looking_for": looking_for,  # Send as string, let backend handle parsing
                "looking_for_list": [role.strip() for role in looking_for.split(",") if role.strip()],  # List of roles
                "pitch_deck_url": "https://example.com/pitch-deck",  # Valid URL
                "website": "https://example.com",  # Valid URL
                "funding_stage": form_data.get("funding_stage") or "Pre-seed",
                "investment_needed": "0.00",  # String format as in example
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

    def toggle_join_request_modal(self, project: Optional[Project] = None):
        """Toggle the join request modal."""
        self.show_join_request_modal = not self.show_join_request_modal
        self.selected_project = project if project else None
        if not self.show_join_request_modal:
            self.join_request_message = ""
            self.error = None
    
    async def send_join_request(self):
        """Send a request to join a project."""
        try:
            if not self.selected_project:
                self.error = "No project selected"
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Prepare join request data
            request_data = {
                "message": self.join_request_message.strip()
            }
            
            print(f"Sending request to join startup group: {self.selected_project.name} (ID: {self.selected_project.id})")
            print(f"Request data: {request_data}")
            
            async with httpx.AsyncClient() as client:
                # First, verify the project exists using the public endpoint
                try:
                    verify_response = await client.get(
                        f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/",
                        headers=headers
                    )
                    print(f"Project verification response: {verify_response.status_code}")
                    print(f"Project verification content: {verify_response.text}")
                    
                    if verify_response.status_code == 404:
                        self.error = "Project not found. Please refresh the page and try again."
                        return
                except Exception as e:
                    print(f"Error verifying project: {str(e)}")
                    self.error = "Error verifying project. Please try again later."
                    return
                
                # Try the join request endpoint
                try:
                    response = await client.post(
                        f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/request-to-join/",  # Changed to correct endpoint
                        json=request_data,
                        headers=headers
                    )
                    
                    print(f"Join request response: {response.status_code}")
                    print(f"Join request content: {response.text}")
                    
                    if response.status_code in [200, 201]:
                        self.show_join_request_modal = False
                        self.selected_project = None
                        self.join_request_message = ""
                        # Show success notification
                        self.show_success_notification(
                            "Join Request Sent",
                            "Your request to join the project has been sent successfully. The project owner will be notified by email."
                        )
                    else:
                        error_data = response.json()
                        self.error = error_data.get("error", "Failed to send join request")
                        print(f"Error sending join request: {response.text}")
                except Exception as e:
                    print(f"Error sending join request: {str(e)}")
                    self.error = "Failed to send join request. Please try again later."
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in send_join_request: {str(e)}")
    
    def show_success_notification(self, title: str, message: str):
        """Show a success notification."""
        # You can implement a notification system here
        print(f"Success: {title} - {message}")

    async def toggle_join_requests_modal(self, project: Optional[Project] = None):
        """Toggle the join requests modal."""
        self.show_join_requests_modal = not self.show_join_requests_modal
        self.selected_project = project if project else None
        if self.show_join_requests_modal and project:
            await self.load_join_requests(project)
        if not self.show_join_requests_modal:
            self.join_requests = []
            self.error = None

    async def load_join_requests(self, project: Project):
        """Load join requests for a project."""
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/startup-profile/startup-ideas/{project.id}/project-join-requests/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.join_requests = [
                        JoinRequest(
                            id=req["id"],
                            project_name=req["project_name"],
                            sender_name=req["sender_name"],
                            sender_id=req["sender_id"],
                            status=req["status"],
                            message=req["message"],
                            created_at=req["created_at"]
                        )
                        for req in data.get("join_requests", [])
                    ]
                elif response.status_code == 401:
                    return rx.redirect("/login")
                else:
                    self.error = f"Failed to load join requests: {response.text}"
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in load_join_requests: {str(e)}")

    async def accept_join_request(self, request_id: int, sender_id: int):
        """Accept a join request and add the sender as a project member."""
        try:
            if not self.selected_project:
                self.error = "No project selected"
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Find the join request to get the sender's username
            join_request = next((req for req in self.join_requests if req.id == request_id), None)
            if not join_request:
                self.error = "Join request not found"
                return
            
            # First, add the member to the project
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/add_member/",
                    json={"user_id": sender_id, "username": join_request.sender_name},  # Use sender's username from the request
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Update the join request status
                    update_response = await client.patch(
                        f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/project-join-requests/{request_id}/",
                        json={"status": "accepted"},
                        headers=headers
                    )
                    
                    if update_response.status_code == 200:
                        # Delete the join request using the correct endpoint
                        delete_response = await client.delete(
                            f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/join-request/{request_id}/",
                            headers=headers
                        )
                        
                        if delete_response.status_code == 204:
                            # Update the local list immediately
                            self.join_requests = [req for req in self.join_requests if req.id != request_id]
                            # Then reload to ensure we have the latest data
                            await self.load_join_requests(self.selected_project)
                            self.show_success_notification(
                                "Request Accepted",
                                "The user has been added to your project and the request has been deleted."
                            )
                        else:
                            self.error = f"Failed to delete request: {delete_response.text}"
                    else:
                        self.error = f"Failed to update request status: {update_response.text}"
                else:
                    self.error = f"Failed to add member: {response.text}"
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in accept_join_request: {str(e)}")

    async def reject_join_request(self, request_id: int):
        """Reject a join request."""
        try:
            if not self.selected_project:
                self.error = "No project selected"
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Find the join request
            join_request = next((req for req in self.join_requests if req.id == request_id), None)
            if not join_request:
                self.error = "Join request not found"
                return
            
            async with httpx.AsyncClient() as client:
                # Update the join request status to rejected
                update_response = await client.patch(
                    f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/project-join-requests/{request_id}/",
                    json={"status": "rejected"},
                    headers=headers
                )
                
                if update_response.status_code == 200:
                    # Delete the join request
                    delete_response = await client.delete(
                        f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/join-request/{request_id}/",
                        headers=headers
                    )
                    
                    if delete_response.status_code == 204:
                        # Update the local list immediately
                        self.join_requests = [req for req in self.join_requests if req.id != request_id]
                        # Then reload to ensure we have the latest data
                        await self.load_join_requests(self.selected_project)
                        self.show_success_notification(
                            "Request Rejected",
                            "The join request has been rejected and deleted."
                        )
                    else:
                        self.error = f"Failed to delete request: {delete_response.text}"
                else:
                    self.error = f"Failed to update request status: {update_response.text}"
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in reject_join_request: {str(e)}")

    async def delete_join_request(self, request_id: int):
        """Delete a join request."""
        try:
            if not self.selected_project:
                self.error = "No project selected"
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.API_URL}/startup-profile/startup-ideas/{self.selected_project.id}/join-request/{request_id}/",
                    headers=headers
                )
                
                if response.status_code == 204:
                    # Reload the join requests to show updated list
                    await self.load_join_requests(self.selected_project)
                    self.show_success_notification(
                        "Request Deleted",
                        "The join request has been deleted successfully."
                    )
                else:
                    self.error = f"Failed to delete request: {response.text}"
                    
        except Exception as e:
            self.error = str(e)
            print(f"Exception in delete_join_request: {str(e)}")