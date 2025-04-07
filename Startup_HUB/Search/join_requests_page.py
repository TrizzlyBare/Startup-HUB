import reflex as rx
import httpx
import json
from typing import List, Optional
from ..Auth.AuthPage import AuthState

class JoinRequest(rx.Base):
    """A join request model."""
    id: int
    project_name: str
    sender_name: str
    sender_id: int
    status: str
    message: str
    created_at: str

class JoinRequestsState(rx.State):
    """The state for the join requests page."""
    
    # API endpoint - base URL
    API_URL = "http://startup-hub:8000/api/startup-profile"
    
    # Join requests list
    join_requests: List[JoinRequest] = []
    
    # Project info
    project_name: str = ""
    current_project_id: int = 0
    
    # Error handling
    error: Optional[str] = None
    
    # Loading state
    is_loading: bool = True
    
    # Debug info
    debug_info: str = ""
    
    # Notification states
    show_notification: bool = False
    notification_type: str = "info"
    notification_title: str = ""
    notification_message: str = ""

    def hide_notification(self):
        """Hide the notification."""
        self.show_notification = False

    def add_debug_info(self, info: str):
        """Add debug information to display."""
        print(f"Debug: {info}")  # Print to console
        self.debug_info = f"{self.debug_info}\n{info}"  # Add to UI debug info

    async def on_mount(self):
        """Load join requests when the component mounts."""
        self.debug_info = ""  # Clear previous debug info
        self.is_loading = True
        self.error = None
        self.add_debug_info("Component mounted")
        
        try:
            if not hasattr(self, "router"):
                self.add_debug_info("No router found")
                self.error = "Router not initialized"
                return

            params = getattr(self.router.page, "params", {})
            self.add_debug_info(f"URL parameters: {params}")
            
            if "id" not in params:
                self.add_debug_info("No project ID in URL")
                self.error = "No project ID provided"
                return
            
            try:
                project_id = int(params["id"])
                self.add_debug_info(f"Extracted project ID: {project_id}")
                self.current_project_id = project_id
                await self.load_join_requests()
            except ValueError:
                self.add_debug_info(f"Invalid project ID: {params['id']}")
                self.error = "Invalid project ID"
                
        except Exception as e:
            error_msg = f"Error in on_mount: {str(e)}"
            self.add_debug_info(error_msg)
            self.error = error_msg
        finally:
            if not self.error:
                self.is_loading = False
    
    async def load_join_requests(self):
        """Load join requests for the project."""
        self.add_debug_info(f"\nLoading join requests for project {self.current_project_id}")
        self.is_loading = True
        self.error = None
        
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                self.add_debug_info(f"Token from localStorage: {'Found' if auth_token else 'Not found'}")
                
                if auth_token:
                    auth_state.set_token(auth_token)
                    self.add_debug_info("Token set in AuthState")
                else:
                    self.add_debug_info("No auth token found, redirecting to login")
                    self.error = "Please log in to view join requests"
                    return rx.redirect("/login")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}",
                "Accept": "application/json",
            }
            self.add_debug_info(f"Request headers: {json.dumps(headers, default=str)}")
            
            url = f"{self.API_URL}/startup-ideas/{self.current_project_id}/project-join-requests/"
            self.add_debug_info(f"Making API request to: {url}")
            
            # Create client with debug logging
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
                self.add_debug_info("Sending API request...")
                try:
                    # Make the request
                    self.add_debug_info("Starting request...")
                    response = await client.get(url, headers=headers)
                    self.add_debug_info(f"Request completed with status: {response.status_code}")
                    self.add_debug_info(f"Response headers: {dict(response.headers)}")
                    
                    # Log the raw response
                    raw_response = response.text
                    self.add_debug_info(f"Raw response: {raw_response}")
                    
                    if response.status_code == 200:
                        try:
                            # Parse the JSON response
                            data = response.json()
                            self.add_debug_info(f"Successfully parsed JSON response: {json.dumps(data, indent=2)}")
                            
                            # Extract project name
                            self.project_name = data.get("project_name", "")
                            self.add_debug_info(f"Project name: {self.project_name}")
                            
                            # Extract join requests
                            join_requests_data = data.get("join_requests", [])
                            self.add_debug_info(f"Found {len(join_requests_data)} join requests")
                            
                            # Create JoinRequest objects
                            self.join_requests = []  # Clear existing requests
                            for request_data in join_requests_data:
                                try:
                                    request = JoinRequest(**request_data)
                                    self.join_requests.append(request)
                                    self.add_debug_info(f"Added request: {request_data}")
                                except Exception as e:
                                    self.add_debug_info(f"Error creating request object: {str(e)}")
                            
                            self.add_debug_info(f"Successfully loaded {len(self.join_requests)} join requests")
                            self.error = None
                            
                        except json.JSONDecodeError as e:
                            self.error = "Invalid response format from server"
                            self.add_debug_info(f"JSON decode error: {str(e)}")
                            self.add_debug_info(f"Raw content that failed to parse: {raw_response}")
                    elif response.status_code == 401:
                        self.error = "Please log in to view join requests"
                        self.add_debug_info("Authentication failed - redirecting to login")
                        return rx.redirect("/login")
                    elif response.status_code == 403:
                        self.error = "You don't have permission to view these join requests"
                        self.add_debug_info("Permission denied")
                    elif response.status_code == 404:
                        self.error = "Project not found"
                        self.add_debug_info(f"Project with ID {self.current_project_id} not found")
                    else:
                        self.error = f"Failed to load join requests: {response.text}"
                        self.add_debug_info(f"Unexpected status code: {response.status_code}")
                except httpx.TimeoutException:
                    self.error = "Request timed out. Please try again."
                    self.add_debug_info("API request timed out")
                except httpx.RequestError as e:
                    self.error = f"Network error: {str(e)}"
                    self.add_debug_info(f"Network error occurred: {str(e)}")
        except Exception as e:
            error_msg = f"Error loading join requests: {str(e)}"
            self.add_debug_info(f"Exception: {error_msg}")
            self.error = error_msg
        finally:
            self.is_loading = False
            self.add_debug_info("Request completed")
    
    async def handle_request(self, request_id: int, action: str):
        """Handle a join request (accept or reject)."""
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
                "Authorization": f"Token {auth_token}",
                "X-Request-ID": f"handle_request_{request_id}_{action}_{rx.random.randint(1000, 9999)}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/startup-ideas/{self.current_project_id}/join-requests/{request_id}/{action}/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    await self.load_join_requests()
                    self.show_success_notification(
                        "Request Handled",
                        f"Successfully {action}ed the join request."
                    )
                else:
                    self.show_error_notification(
                        "Error",
                        f"Failed to {action} request. Please try again."
                    )
        except Exception as e:
            self.error = str(e)
            print(f"Error handling request: {str(e)}")
    
    def show_success_notification(self, title: str, message: str):
        """Show a success notification."""
        self.notification_type = "success"
        self.notification_title = title
        self.notification_message = message
        self.show_notification = True
    
    def show_error_notification(self, title: str, message: str):
        """Show an error notification."""
        self.notification_type = "error"
        self.notification_title = title
        self.notification_message = message
        self.show_notification = True

def show_join_request(request: JoinRequest) -> rx.Component:
    """Show a join request component."""
    return rx.box(
        rx.vstack(
            # User info
            rx.hstack(
                rx.avatar(
                    fallback=request.sender_name[0].upper(),
                    size="5",
                ),
                rx.vstack(
                    rx.text(request.sender_name, class_name="font-bold"),
                    rx.text(f"ID: {request.sender_id}", class_name="text-sm text-gray-500"),
                    align_items="start",
                ),
                spacing="3",
                width="100%",
            ),
            # Request message
            rx.cond(
                request.message,
                rx.text(
                    request.message,
                    class_name="text-gray-700 p-4 bg-gray-50 rounded-lg",
                ),
                rx.text(
                    "No message provided",
                    class_name="text-gray-500 p-4 bg-gray-50 rounded-lg italic",
                ),
            ),
            # Request info
            rx.hstack(
                rx.text(f"Status: {request.status}", class_name="text-sm text-gray-500"),
                rx.text(f"Requested: {request.created_at}", class_name="text-sm text-gray-500"),
                spacing="4",
            ),
            # Action buttons
            rx.hstack(
                rx.button(
                    "Accept",
                    on_click=lambda: JoinRequestsState.handle_request(request.id, "accept"),
                    class_name="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg",
                ),
                rx.button(
                    "Reject",
                    on_click=lambda: JoinRequestsState.handle_request(request.id, "reject"),
                    class_name="bg-red-600 text-white hover:bg-red-700 px-4 py-2 rounded-lg",
                ),
                spacing="4",
                justify="end",
                width="100%",
            ),
            spacing="4",
            padding="4",
            border="1px solid",
            border_color="gray.200",
            border_radius="lg",
            width="100%",
        ),
        class_name="bg-white shadow-md rounded-lg",
    )

def notification():
    """Custom notification component."""
    return rx.cond(
        JoinRequestsState.show_notification,
        rx.box(
            rx.hstack(
                rx.cond(
                    JoinRequestsState.notification_type == "success",
                    rx.icon("check", color="white", size=6),
                    rx.icon("alert-triangle", color="white", size=6)
                ),
                rx.vstack(
                    rx.text(
                        JoinRequestsState.notification_title,
                        font_weight="bold",
                        color="white",
                    ),
                    rx.text(
                        JoinRequestsState.notification_message,
                        color="white",
                    ),
                    align_items="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("x", size=4),
                    on_click=JoinRequestsState.hide_notification,
                    variant="ghost",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="3",
            ),
            position="fixed",
            bottom="4",
            right="4",
            max_width="400px",
            p="4",
            border_radius="md",
            z_index="1000",
            shadow="lg",
            bg=rx.cond(
                JoinRequestsState.notification_type == "success",
                "green.500",
                "red.500"
            ),
            opacity="0.95",
        ),
        rx.fragment()
    )

@rx.page(route="/projects/[id]/join-requests")
def join_requests_page() -> rx.Component:
    """The join requests page."""
    return rx.vstack(
        rx.container(
            rx.vstack(
                rx.heading(
                    rx.cond(
                        JoinRequestsState.project_name,
                        f"Join Requests for {JoinRequestsState.project_name}",
                        "Join Requests"
                    ),
                    size="6",
                    class_name="text-2xl font-bold mb-6 text-sky-600",
                ),
                # Debug information
                rx.cond(
                    JoinRequestsState.debug_info,
                    rx.box(
                        rx.text_area(
                            value=JoinRequestsState.debug_info,
                            is_read_only=True,
                            class_name="font-mono text-xs",
                            width="100%",
                            height="200px",
                            bg="gray.50",
                            color="gray.800",
                            padding="4",
                            border_radius="md",
                            white_space="pre",
                        ),
                        margin_bottom="4",
                    ),
                ),
                # Loading state
                rx.cond(
                    JoinRequestsState.is_loading,
                    rx.center(
                        rx.vstack(
                            rx.spinner(
                                size="3",
                                color="rgb(59 130 246)",
                            ),
                            rx.text("Loading join requests...", class_name="text-gray-500 mt-2"),
                            padding="8",
                        ),
                    ),
                ),
                # Error message
                rx.cond(
                    JoinRequestsState.error,
                    rx.box(
                        rx.text(
                            JoinRequestsState.error,
                            class_name="text-red-500",
                        ),
                        padding="4",
                        bg="red.50",
                        border_radius="md",
                        margin_bottom="4",
                    ),
                ),
                # Join requests list
                rx.cond(
                    ~JoinRequestsState.is_loading,
                    rx.cond(
                        JoinRequestsState.join_requests.length() > 0,
                        rx.vstack(
                            rx.foreach(
                                JoinRequestsState.join_requests,
                                show_join_request
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        rx.text(
                            "No join requests found.",
                            class_name="text-gray-500 text-center",
                        ),
                    ),
                ),
                spacing="6",
                width="100%",
                padding="8",
            ),
            max_width="800px",
            width="100%",
        ),
        notification(),
        class_name="min-h-screen bg-gray-50",
    ) 