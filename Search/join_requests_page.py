# API endpoint - base URL
API_URL = "http://startup-hub:8000/api/startup-profile"

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

    def add_debug_info(self, info: str):
        """Add debug information to display."""
        print(f"Debug: {info}")  # Print to console for terminal debugging
        self.debug_info = f"{self.debug_info}\n{info}"  # Add to UI debug info
        return self.debug_info  # Return for chaining

async def load_join_requests(self):
    """Load join requests for the project."""
    self.debug_info = ""  # Clear previous debug info
    self.add_debug_info(f"Starting to load join requests for project {self.current_project_id}")
    
    if not self.current_project_id:
        self.error = "No project ID available"
        self.add_debug_info("current_project_id is not set")
        self.is_loading = False
        return
        
    try:
        # Get auth token
        auth_state = await self.get_state(AuthState)
        auth_token = auth_state.token if auth_state else None
        
        if not auth_token:
            auth_token = await rx.call_script("localStorage.getItem('auth_token')")
            self.add_debug_info("Retrieved token from localStorage")
        
        if not auth_token:
            self.error = "No authentication token found"
            self.add_debug_info("No auth token found - cannot proceed")
            self.is_loading = False
            return
        
        headers = {
            "Authorization": f"Token {auth_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        url = f"{self.API_URL}/startup-ideas/{self.current_project_id}/project-join-requests/"
        self.add_debug_info(f"Making request to: {url}")
        self.add_debug_info(f"With headers: {headers}")
        
        async with httpx.AsyncClient(verify=False) as client:
            self.add_debug_info("Sending API request...")
            try:
                response = await client.get(url, headers=headers)
                self.add_debug_info(f"Response status: {response.status_code}")
                self.add_debug_info(f"Response headers: {dict(response.headers)}")
                self.add_debug_info(f"Response content: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.add_debug_info(f"Received data: {data}")
                    
                    if isinstance(data, dict) and "join_requests" in data:
                        join_requests_data = data["join_requests"]
                        self.join_requests = [JoinRequest(**request) for request in join_requests_data]
                        self.add_debug_info(f"Processed {len(self.join_requests)} join requests")
                        if "project_name" in data:
                            self.project_name = data["project_name"]
                    elif isinstance(data, list):
                        self.join_requests = [JoinRequest(**request) for request in data]
                        self.add_debug_info(f"Processed {len(self.join_requests)} join requests from list")
                    else:
                        self.error = "Invalid response format"
                        self.add_debug_info(f"Unexpected response format: {data}")
                else:
                    self.error = f"Server returned {response.status_code}: {response.text}"
                    self.add_debug_info(f"Error response: {response.text}")
            
            except httpx.RequestError as e:
                self.error = f"Network error: {str(e)}"
                self.add_debug_info(f"Request error: {str(e)}")
            except json.JSONDecodeError as e:
                self.error = "Invalid JSON response from server"
                self.add_debug_info(f"JSON decode error: {str(e)}")
                self.add_debug_info(f"Raw response: {response.text}")
            except Exception as e:
                self.error = f"Unexpected error: {str(e)}"
                self.add_debug_info(f"Unexpected error: {str(e)}")
    
    except Exception as e:
        self.error = f"Error: {str(e)}"
        self.add_debug_info(f"Top-level error: {str(e)}")
    
    finally:
        self.is_loading = False
        self.add_debug_info("Request completed")

async def on_mount(self):
    """Load join requests when the component mounts."""
    print("=== Component Mount Started ===")  # Immediate console output
    
    self.debug_info = ""  # Clear previous debug info
    self.is_loading = True
    self.error = None
    
    print("Initializing component...")  # Immediate console output
    self.add_debug_info("Component mounted")
    
    try:
        # Get the project ID from route parameters
        if not hasattr(self, "router"):
            print("No router found")  # Immediate console output
            self.add_debug_info("No router found")
            self.error = "Router not initialized"
            return

        print(f"Router found: {self.router}")  # Immediate console output
        project_id = self.router.page.params.get("id")
        print(f"Project ID from params: {project_id}")  # Immediate console output
        self.add_debug_info(f"Got project ID from route params: {project_id}")
        
        if not project_id:
            print("No project ID in URL")  # Immediate console output
            self.add_debug_info("No project ID in URL")
            self.error = "No project ID provided"
            return
        
        # Set the current project ID
        self.current_project_id = project_id
        print(f"Set current_project_id to: {self.current_project_id}")  # Immediate console output
        self.add_debug_info(f"Set current_project_id to: {self.current_project_id}")
        
        # Load the join requests
        print("Starting to load join requests...")  # Immediate console output
        await self.load_join_requests()
        
    except Exception as e:
        error_msg = f"Error in on_mount: {str(e)}"
        print(f"Error: {error_msg}")  # Immediate console output
        self.add_debug_info(error_msg)
        self.error = error_msg
        self.is_loading = False
    
    print("=== Component Mount Completed ===")  # Immediate console output 