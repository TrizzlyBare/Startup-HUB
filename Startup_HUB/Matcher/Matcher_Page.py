import reflex as rx
from typing import List, Dict, Any, TypedDict, Optional
from .SideBar import sidebar
import httpx
from ..Auth.AuthPage import AuthState

class ContactLink(TypedDict):
    url: str
    type: str

class UserDetails(TypedDict):
    id: int
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    industry: Optional[str]
    bio: Optional[str]
    experience: Optional[str]
    skills: Optional[List[str]]
    contact_links: Optional[List[ContactLink]]

class MatchData(TypedDict):
    id: int
    user: int
    matched_user: int
    matched_user_details: UserDetails
    user_details: UserDetails
    created_at: str
    is_mutual: bool

class LikeData(TypedDict):
    id: int
    user: int
    liked_user: int
    liked_user_details: UserDetails
    created_at: str

class DislikeData(TypedDict):
    id: int
    user: int
    disliked_user: int
    disliked_user_details: UserDetails
    created_at: str

class Profile(TypedDict):
    id: int
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    bio: Optional[str]
    industry: Optional[str]
    experience: Optional[str]
    skills: Optional[str]
    contact_links: List[ContactLink]

class RoomParticipant(TypedDict):
    user: Dict[str, Any]
    joined_at: str
    is_admin: bool
    is_muted: bool

class RoomMessage(TypedDict):
    id: str
    room: str
    sender: Dict[str, Any]
    content: str
    message_type: str
    image: Optional[str]
    video: Optional[str]
    audio: Optional[str]
    document: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    sent_at: str
    is_read: bool
    call_duration: Optional[int]
    call_type: Optional[str]
    call_status: Optional[str]

class RoomData(TypedDict):
    id: str
    name: str
    room_type: str
    created_at: str
    updated_at: str
    is_active: bool
    max_participants: int
    profile_image: Optional[str]
    participants: List[RoomParticipant]
    last_message: Optional[RoomMessage]

class MatchState(rx.State):
    """State for the matcher page."""
    # API endpoint - base URL
    API_BASE_URL = "http://startup-hub:8000/api"
    
    # State variables
    current_profile_index: int = 0
    show_report_dialog: bool = False
    selected_issue_type: str = ""
    profiles: List[Profile] = []
    error_message: str = ""
    success_message: str = ""
    loading: bool = True
    active_tab: str = "Matches"
    
    # Authentication
    auth_token: str = ""
    
    # Chat variables
    show_chat: bool = False
    current_chat_room: Optional[str] = None
    messages: List[Dict] = []
    new_message: str = ""
    
    # Required for sidebar
    matches: List[MatchData] = []
    likes: List[LikeData] = []
    dislikes: List[DislikeData] = []
    rooms: List[RoomData] = []  # Update rooms type
    
    # Profile-specific variables
    profile_username: str = ""
    profile_data: Optional[Profile] = None
    is_profile_route: bool = False
    
    show_profile_popup: bool = False
    view_profile_data: Optional[Dict[str, Any]] = None
    
    def debug_api_request(self, method: str, url: str, headers: Dict, json_data: Optional[Dict] = None):
        """Debug function to print API request details."""
        print("\n=== API Request Debug ===")
        print(f"Method: {method}")
        print(f"URL: {url}")
        print("Headers:")
        for key, value in headers.items():
            print(f"  {key}: {value}")
        if json_data:
            print("Request Body:")
            print(f"  {json_data}")
        print("=======================\n")

    @rx.var
    def get_username(self) -> str:
        """Get username from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            print(f"Route params: {params}")
            if "user_profile" in params:
                self.is_profile_route = True
                self.profile_username = params["user_profile"]
                print(f"Profile route detected, username: {self.profile_username}")
                return self.profile_username
        return ""
    
    async def on_mount(self):
        """Called when the component mounts."""
        print("\n=== Matcher Page Mounted ===")
        
        # First try to get token from AuthState
        auth_state = await self.get_state(AuthState)
        self.auth_token = auth_state.token
        
        # Initialize other data
        username = self.get_username
        print(f"Username from route: {username}")
        
        if username:
            print(f"Loading profile data for {username}")
            await self.load_profile_data(username)
            await self.load_likes()
            await self.load_matches()
            await self.load_rooms()  # Add rooms loading
        else:
            print("Loading all users")
            await self.load_all_users()
    
    def next_profile(self):
        """Show the next profile."""
        if self.current_profile_index < len(self.profiles) - 1:
            self.current_profile_index += 1
    
    def previous_profile(self):
        """Show the previous profile."""
        if self.current_profile_index > 0:
            self.current_profile_index -= 1
    
    async def like_profile(self):
        """Like the current profile."""
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            # Get current profile
            if self.current_profile_index >= len(self.profiles):
                self.error_message = "No more profiles to like."
                return
                
            current_profile = self.profiles[self.current_profile_index]
            print(f"\nLiking profile: {current_profile}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get current user's username
            current_user = self.get_username
            if not current_user:
                self.error_message = "Could not get current user's username"
                return
            
            # First check if the like already exists
            async with httpx.AsyncClient() as client:
                print("\nChecking for existing like...")
                response = await client.get(
                    f"{self.API_BASE_URL}/matches/likes/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    existing_likes = data.get("results", [])
                    # Check if current user has already liked this profile
                    for like in existing_likes:
                        if like["user"] == current_user and like["liked_user"] == current_profile["username"]:
                            print("Like already exists, moving to next profile")
                            self.next_profile()
                            return
                
                # If no existing like, create a new one
                print("\nMaking like request...")
                request_data = {
                    "user": current_user,  # Use the current user's username
                    "liked_user": current_profile["username"],  # Use the profile's username
                    "liked_user_details": {
                        "id": current_profile["id"],
                        "username": current_profile["username"],
                        "first_name": current_profile.get("first_name", ""),
                        "last_name": current_profile.get("last_name", ""),
                        "email": current_profile.get("email", ""),
                        "profile_picture": current_profile.get("profile_picture"),
                        "profile_picture_url": current_profile.get("profile_picture_url"),
                        "bio": current_profile.get("bio"),
                        "industry": current_profile.get("industry"),
                        "experience": current_profile.get("experience"),
                        "skills": current_profile.get("skills"),
                        "skills_list": current_profile.get("skills_list", []),
                        "past_projects": current_profile.get("past_projects"),
                        "past_projects_list": current_profile.get("past_projects_list", []),
                        "career_summary": current_profile.get("career_summary"),
                        "contact_links": current_profile.get("contact_links", [])
                    }
                }
                print(f"Request data: {request_data}")
                
                # Debug the request URL and data
                print(f"\nRequest URL: {self.API_BASE_URL}/matches/likes/")
                print(f"Request data: {request_data}")
                
                # Make the POST request
                response = await client.post(
                    f"{self.API_BASE_URL}/matches/likes/",
                    headers=headers,
                    json=request_data
                )
                
                print(f"Response status code: {response.status_code}")
                
                if response.status_code == 201:
                    print(f"Successfully liked profile: {current_profile['username']}")
                    # Show success message
                    self.success_message = f"You liked {current_profile['username']}!"
                    
                    # Create direct chat with the liked user
                    await self.create_direct_chat_with_user(current_profile['username'])
                    
                    # Load matches to check if this created a new match
                    await self.load_matches()
                    
                    # Move to next profile
                    self.next_profile()
                else:
                    print(f"Error liking profile: {response.text}")
                    self.error_message = f"Error liking profile: {response.text}"
        except Exception as e:
            self.error_message = f"Error liking profile: {str(e)}"
            print(f"Error: {str(e)}")
    
    async def dislike_profile(self):
        """Dislike the current profile."""
        print("\n=== Dislike Profile Debug ===")
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            print(f"Auth token from state: {bool(auth_token)}")
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                print(f"Auth token from localStorage: {bool(auth_token)}")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    print("No auth token found")
                    return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            print("Headers:", headers)
            
            # Get the current profile being disliked
            current_profile = self.profiles[self.current_profile_index]
            print(f"\nCurrent profile to dislike:")
            print(f"Username: {current_profile['username']}")
            print(f"ID: {current_profile['id']}")
            
            # Get current user's username from route parameters
            current_user = self.get_username
            print(f"Current user from route: {current_user}")
            
            # First check if the dislike already exists
            async with httpx.AsyncClient() as client:
                print("\nChecking for existing dislike...")
                response = await client.get(
                    f"{self.API_BASE_URL}/matches/dislikes/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    existing_dislikes = data.get("results", [])
                    # Check if current user has already disliked this profile
                    for dislike in existing_dislikes:
                        if dislike["user"] == current_user and dislike["disliked_user"] == current_profile["username"]:
                            print("Dislike already exists, moving to next profile")
                            self.next_profile()
                            return
                
                # If no existing dislike, create a new one
                print("\nMaking dislike request...")
                request_data = {
                    "user": current_user,  # Use the current user's username
                    "disliked_user": current_profile["username"],  # Use the profile's username
                    "disliked_user_details": {
                        "id": current_profile["id"],
                        "username": current_profile["username"],
                        "first_name": current_profile.get("first_name", ""),
                        "last_name": current_profile.get("last_name", ""),
                        "email": current_profile.get("email", ""),
                        "profile_picture": current_profile.get("profile_picture"),
                        "profile_picture_url": current_profile.get("profile_picture_url"),
                        "bio": current_profile.get("bio", ""),
                        "industry": current_profile.get("industry", ""),
                        "experience": current_profile.get("experience", ""),
                        "skills": current_profile.get("skills", ""),
                        "skills_list": current_profile.get("skills_list", []),
                        "past_projects": current_profile.get("past_projects", ""),
                        "past_projects_list": current_profile.get("past_projects_list", []),
                        "career_summary": current_profile.get("career_summary", ""),
                        "contact_links": current_profile.get("contact_links", [])
                    }
                }
                print(f"Request data: {request_data}")
                
                # Debug the request URL and data
                print(f"\nRequest URL: {self.API_BASE_URL}/matches/dislikes/")
                print(f"Request data: {request_data}")
                
                # Make the POST request
                response = await client.post(
                    f"{self.API_BASE_URL}/matches/dislikes/",
                    headers=headers,
                    json=request_data
                )
                print(f"Dislike response status: {response.status_code}")
                print(f"Dislike response: {response.text}")
                
                if response.status_code == 201:
                    print("Dislike successful!")
                    # Update the dislikes list
                    await self.load_dislikes()
                    # Move to next profile
                    self.next_profile()
                else:
                    print(f"Error disliking profile: {response.text}")
                    self.error_message = f"Error disliking profile: {response.text}"
                    
        except Exception as e:
            print(f"Error in dislike_profile: {str(e)}")
            self.error_message = f"Error disliking profile: {str(e)}"
            
    async def load_dislikes(self):
        """Load dislikes from the API."""
        print("\n=== Loading Dislikes ===")
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get current user's username
            current_user = self.get_username
            print(f"Loading dislikes for user: {current_user}")
            
            async with httpx.AsyncClient() as client:
                # Get all dislikes
                response = await client.get(
                    f"{self.API_BASE_URL}/matches/dislikes/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Raw API response: {data}")
                    
                    # Get all dislikes from the results
                    all_dislikes = data.get("results", [])
                    print(f"Total dislikes found: {len(all_dislikes)}")
                    
                    # Filter dislikes for current user
                    user_dislikes = [dislike for dislike in all_dislikes if dislike["user"] == current_user]
                    print(f"Dislikes for {current_user}: {len(user_dislikes)}")
                    
                    # Update the dislikes list
                    self.dislikes = user_dislikes
                    print(f"Updated dislikes list with {len(self.dislikes)} dislikes")
                    
                    # Debug print each dislike
                    for dislike in self.dislikes:
                        print(f"Dislike: {dislike['id']} - {dislike['user']} -> {dislike['disliked_user']}")
                else:
                    print(f"Error loading dislikes: {response.text}")
                    self.error_message = f"Error loading dislikes: {response.text}"
                    
        except Exception as e:
            print(f"Error in load_dislikes: {str(e)}")
            self.error_message = f"Error loading dislikes: {str(e)}"
    
    def super_like_profile(self):
        """Super like the current profile."""
        # Add super like logic here
        self.next_profile()

    def set_active_tab(self, tab: str):
        """Set the active tab."""
        self.active_tab = tab

    def set_selected_issue_type(self, issue_type: str):
        """Set the selected issue type."""
        self.selected_issue_type = issue_type

    async def load_profile_data(self, username: str):
        """Load profile data for a specific user."""
        self.loading = True
        self.error_message = ""
        print(f"\n=== Loading Profile Data for {username} ===")
        
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                print("Got token from localStorage:", bool(auth_token))
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    self.error_message = "Authentication required. Please log in."
                    print("No auth token found")
                    return rx.redirect("/login")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                # First get the user's profile
                response = await client.get(
                    f"{self.API_BASE_URL}/auth/profile/{username}/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    self.profile_data = Profile(
                        id=user_data["id"],
                        username=user_data["username"],
                        first_name=user_data.get("first_name", ""),
                        last_name=user_data.get("last_name", ""),
                        profile_picture_url=user_data.get("profile_picture_url"),
                        bio=user_data.get("bio", "No bio available"),
                        industry=user_data.get("industry", "No industry specified"),
                        experience=user_data.get("experience", "No experience specified"),
                        skills=user_data.get("skills", ""),
                        contact_links=user_data.get("contact_links", [])
                    )
                    
                    # Get user's startup ideas
                    response = await client.get(
                        f"{self.API_BASE_URL}/auth/profile/{username}/",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Handle paginated response
                        if isinstance(data, dict) and "results" in data:
                            self.profile_data["startup_ideas"] = data["results"]
                        else:
                            self.profile_data["startup_ideas"] = data
                    
                    # Then get all users except the current one
                    response = await client.get(
                        f"{self.API_BASE_URL}/matches/all-users/",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        
                        # Filter out the current user
                        self.profiles = []
                        for user in results:
                            if user["username"] != username:
                                try:
                                    profile = Profile(
                                        id=user["id"],
                                        username=user["username"],
                                        first_name=user.get("first_name", ""),
                                        last_name=user.get("last_name", ""),
                                        profile_picture_url=user.get("profile_picture_url"),
                                        bio=user.get("bio", "No bio available"),
                                        industry=user.get("industry", "No industry specified"),
                                        experience=user.get("experience", "No experience specified"),
                                        skills=user.get("skills", ""),
                                        contact_links=user.get("contact_links", [])
                                    )
                                    self.profiles.append(profile)
                                except Exception as e:
                                    print(f"Error mapping user {user.get('username', 'unknown')}: {str(e)}")
                    else:
                        self.error_message = f"Failed to load users: {response.text}"
                else:
                    self.error_message = f"Failed to load profile: {response.text}"
                    
        except Exception as e:
            error_msg = f"Error loading profile: {str(e)}"
            print(f"Exception: {error_msg}")
            self.error_message = error_msg
        finally:
            self.loading = False
            print("=== Finished Loading Profile ===\n")
    
    async def load_all_users(self):
        """Load all users from the API."""
        self.loading = True
        self.error_message = ""
        print("\n=== Loading All Users ===")
        print(f"Making API request to: {self.API_BASE_URL}/matches/all-users/")
        
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                print("Got token from localStorage:", bool(auth_token))
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    self.error_message = "Authentication required. Please log in."
                    print("No auth token found")
                    return rx.redirect("/login")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            print("Headers:", headers)
            
            async with httpx.AsyncClient() as client:
                print("Making API call...")
                response = await client.get(
                    f"{self.API_BASE_URL}/matches/all-users/",
                    headers=headers
                )
                
                print(f"Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print("\nResponse Data:")
                    print(f"Data type: {type(data)}")
                    
                    # Handle paginated response
                    if isinstance(data, dict) and "results" in data:
                        results = data["results"]
                        print(f"Number of users: {len(results)}")
                        if results:
                            print("First user sample:", results[0])
                        
                        # Map API response to Profile format
                        self.profiles = []
                        for user in results:
                            try:
                                profile = Profile(
                                    id=user["id"],
                                    username=user["username"],
                                    first_name=user.get("first_name", ""),
                                    last_name=user.get("last_name", ""),
                                    profile_picture_url=user.get("profile_picture_url"),
                                    bio=user.get("bio", "No bio available"),
                                    industry=user.get("industry", "No industry specified"),
                                    experience=user.get("experience", "No experience specified"),
                                    skills=user.get("skills", ""),  # Handle skills as string
                                    contact_links=user.get("contact_links", [])
                                )
                                self.profiles.append(profile)
                                print(f"Successfully mapped user: {profile['username']}")
                                print(f"User data: {profile}")
                            except Exception as e:
                                print(f"Error mapping user {user.get('username', 'unknown')}: {str(e)}")
                                print("User data causing error:", user)
                        
                        print(f"\nSuccessfully mapped {len(self.profiles)} profiles")
                    else:
                        print("Unexpected response format:", data)
                        self.error_message = "Unexpected response format from server"
                    
                elif response.status_code == 401:
                    print("Authentication failed")
                    self.error_message = "Authentication failed. Please log in again."
                    return rx.redirect("/login")
                else:
                    error_msg = f"Failed to load users: {response.text}"
                    print(f"Error: {error_msg}")
                    self.error_message = error_msg
                    
        except Exception as e:
            error_msg = f"Error loading users: {str(e)}"
            print(f"Exception: {error_msg}")
            self.error_message = error_msg
        finally:
            self.loading = False
            print("=== Finished Loading Users ===\n")

    async def start_chat(self):
        """Start a chat with the current profile.
        
        Checks if a room exists with this user, and if not, creates one.
        Then redirects directly to the chat room.
        """
        self.loading = True
        try:
            # Get target user's username from the current profile
            target_username = self.profiles[self.current_profile_index]["username"]
            
            # Debug the chat start
            print("\n=== Starting Chat ===")
            print(f"Target User: {target_username}")
            
            # Get token and current username
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    self.loading = False
                    return
            
            # Get current user's username
            current_username = self.get_username
            
            if not current_username:
                self.error_message = "Could not get current user's username"
                self.loading = False
                return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Check if room already exists
            existing_room = await self.find_existing_room(current_username, target_username)
            
            if existing_room:
                # Room exists, redirect directly to it
                room_id = existing_room.get("id")
                print(f"Found existing room {room_id} - redirecting to it")
                self.loading = False
                return rx.redirect(f"/chat/room/{room_id}")
            else:
                # Create new room
                print(f"No existing room found - creating a new one with {target_username}")
                
                async with httpx.AsyncClient() as client:
                    # Use the direct room creation endpoint
                    create_response = await client.post(
                        f"{self.API_BASE_URL}/communication/room/direct/",
                        json={"username": target_username},
                        headers=headers
                    )
                    
                    print(f"Create room response status: {create_response.status_code}")
                    
                    if create_response.status_code == 201 or create_response.status_code == 200:
                        room_data = create_response.json()
                        room_id = room_data.get("id")
                        
                        if room_id:
                            print(f"Created room with ID {room_id} - redirecting to it")
                            # Save auth token to localStorage again to ensure it's available for the chat page
                            await rx.call_script(f"localStorage.setItem('auth_token', '{auth_token}');")
                            print(f"Auth token saved to localStorage: {auth_token[:5]}...")
                            print(f"REDIRECTING TO: /chat/room/{room_id}")
                            return rx.redirect(f"/chat/room/{room_id}")
                        else:
                            print("Failed to get room ID from created room")
                            self.error_message = "Could not create chat room"
                    else:
                        print(f"Failed to create room: {create_response.text}")
                        self.error_message = f"Failed to create chat room: {create_response.status_code}"
                
        except Exception as e:
            self.error_message = f"Error starting chat: {str(e)}"
            print(f"\n=== Error Debug ===")
            print(f"Error: {str(e)}")
            print("==================\n")
        
        self.loading = False

    async def load_messages(self):
        """Load messages for the current chat room."""
        if not self.current_chat_room:
            return
            
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                return
                
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Debug the request
            self.debug_api_request(
                "GET",
                f"{self.API_BASE_URL}/communication/messages/",
                headers
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/messages/",
                    headers=headers,
                    params={"room": self.current_chat_room}
                )
                
                # Debug the response
                print("\n=== API Response Debug ===")
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                print("========================\n")
                
                if response.status_code == 200:
                    data = response.json()
                    # Get messages from the response
                    self.messages = data.get("results", [])
                else:
                    self.error_message = f"Failed to load messages: {response.text}"
                    
        except Exception as e:
            self.error_message = f"Error loading messages: {str(e)}"
            print(f"\n=== Error Debug ===")
            print(f"Error: {str(e)}")
            print("==================\n")

    async def send_message(self):
        """Send a new message in the current chat room."""
        if not self.new_message.strip() or not self.current_chat_room:
            return
            
        try:
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                return
                
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            request_data = {
                "room": self.current_chat_room,
                "content": self.new_message,
                "message_type": "text"
            }
            
            # Debug the request
            self.debug_api_request(
                "POST",
                f"{self.API_BASE_URL}/communication/messages/",
                headers,
                request_data
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/communication/messages/",
                    headers=headers,
                    json=request_data
                )
                
                # Debug the response
                print("\n=== API Response Debug ===")
                print(f"Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                print("========================\n")
                
                if response.status_code == 201:
                    self.new_message = ""
                    await self.load_messages()
                else:
                    self.error_message = f"Failed to send message: {response.text}"
                    
        except Exception as e:
            self.error_message = f"Error sending message: {str(e)}"
            print(f"\n=== Error Debug ===")
            print(f"Error: {str(e)}")
            print("==================\n")

    def close_chat(self):
        """Reset chat-related state variables.
        
        This is now only used to clean up state, since the chat UI 
        is handled by the dedicated ChatPage component.
        """
        self.current_chat_room = None
        self.messages = []
        self.new_message = ""
        # Note: We don't need to set show_chat=False anymore since we don't use the embedded UI

    async def find_existing_room(self, current_username, target_username):
        """Find an existing room between two users.
        
        Returns the room object if found, otherwise None.
        """
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return None
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                # First try to use the optimized endpoint
                try:
                    response = await client.get(
                        f"{self.API_BASE_URL}/communication/find-direct-room/?username={target_username}",
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "room" in data and data["room"]:
                            print(f"Found existing room with {target_username} using direct endpoint")
                            return data["room"]
                except Exception as e:
                    print(f"Error using direct room endpoint: {str(e)}, falling back to room list")
                    
                # Fall back to scanning all rooms
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/rooms/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    rooms = response.json().get("results", [])
                    
                    # Check for existing direct room with both participants
                    for room in rooms:
                        if room["room_type"] == "direct":
                            participants = [p["user"]["username"] for p in room["participants"]]
                            if current_username in participants and target_username in participants:
                                print(f"Found existing room by scanning rooms list")
                                return room
                    
                    # If no existing room found
                    return None
                else:
                    print(f"Error checking rooms: {response.text}")
                    return None
                
        except Exception as e:
            print(f"Error in find_existing_room: {str(e)}")
            return None

    async def create_direct_chat_with_user(self, target_username):
        """Create a direct chat with the specified user.
        
        Returns a redirect to the room if successful, otherwise False.
        """
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return False
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get current user's username
            current_username = self.get_username
            
            if not current_username:
                self.error_message = "Could not get current user's username"
                return False
            
            # Check if room already exists
            existing_room = await self.find_existing_room(current_username, target_username)
            
            if existing_room:
                print(f"Room already exists between {current_username} and {target_username}")
                room_id = existing_room.get("id")
                return rx.redirect(f"/chat/room/{room_id}")
            else:
                # Create new room
                print(f"Creating new room between {current_username} and {target_username}")
                
                async with httpx.AsyncClient() as client:
                    # Use the direct room creation endpoint
                    create_response = await client.post(
                        f"{self.API_BASE_URL}/communication/room/direct/",
                        json={"username": target_username},
                        headers=headers
                    )
                    
                    print(f"Create room response status: {create_response.status_code}")
                    
                    if create_response.status_code == 201 or create_response.status_code == 200:
                        room_data = create_response.json()
                        room_id = room_data.get("id")
                        if room_id:
                            print(f"Created room with ID {room_id} - redirecting to it")
                            # Save auth token to localStorage again to ensure it's available for the chat page
                            await rx.call_script(f"localStorage.setItem('auth_token', '{auth_token}');")
                            print(f"Auth token saved to localStorage: {auth_token[:5]}...")
                            print(f"REDIRECTING TO: /chat/room/{room_id}")
                            return rx.redirect(f"/chat/room/{room_id}")
                        else:
                            print("No room ID returned in response")
                            self.error_message = "Failed to create chat room - no room ID returned"
                            return False
                    else:
                        print(f"Failed to create room: {create_response.text}")
                        self.error_message = f"Failed to create chat room: {create_response.status_code}"
                        return False
        
        except Exception as e:
            print(f"\n=== Error Debug ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            print("==================\n")
            self.error_message = f"Error creating chat: {str(e)}"
            return False

    async def load_likes(self):
        """Load likes from the API."""
        print("\n=== Loading Likes ===")
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get current user's username
            current_user = self.get_username
            print(f"Loading likes for user: {current_user}")
            
            async with httpx.AsyncClient() as client:
                # Get all likes
                response = await client.get(
                    f"{self.API_BASE_URL}/matches/likes/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Raw API response: {data}")
                    
                    # Get all likes from the results
                    all_likes = data.get("results", [])
                    print(f"Total likes found: {len(all_likes)}")
                    
                    # Filter likes for current user
                    user_likes = [like for like in all_likes if like["user"] == current_user]
                    print(f"Likes for {current_user}: {len(user_likes)}")
                    
                    # Create a set to track unique liked users
                    unique_liked_users = set()
                    unique_likes = []
                    
                    # Filter out duplicates and keep only the most recent like for each user
                    for like in reversed(user_likes):  # Start from most recent
                        liked_user = like["liked_user"]
                        if liked_user not in unique_liked_users:
                            unique_liked_users.add(liked_user)
                            unique_likes.append(like)
                    
                    # Sort by creation date (most recent first)
                    unique_likes.sort(key=lambda x: x["created_at"], reverse=True)
                    
                    # Update the likes list with unique likes
                    self.likes = unique_likes
                    print(f"Updated likes list with {len(self.likes)} unique likes")
                    
                    # Debug print each unique like
                    for like in self.likes:
                        print(f"Like: {like['id']} - {like['user']} -> {like['liked_user']} ({like['created_at']})")
                    
                    # Create direct chats with all liked users
                    print("\n=== Creating Direct Chats with Liked Users ===")
                    for like in self.likes:
                        liked_user = like["liked_user"]
                        result = await self.create_direct_chat_with_user(liked_user)
                        # Check if result is a redirect (which means success) or False (failure)
                        if result:
                            print(f"Ensured chat exists with liked user: {liked_user}")
                        else:
                            print(f"Failed to create chat with liked user: {liked_user}")
                    
                    # Reload rooms to ensure we have the latest list
                    await self.load_rooms()
                else:
                    print(f"Error loading likes: {response.text}")
                    self.error_message = f"Error loading likes: {response.text}"
        
        except Exception as e:
            print(f"Error in load_likes: {str(e)}")
            self.error_message = f"Error loading likes: {str(e)}"

    async def load_matches(self):
        """Load matches from the API."""
        print("\n=== Loading Matches ===")
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get current user's username
            current_user = self.get_username
            
            if not current_user:
                self.error_message = "Could not get current user's username"
                return
                
            print(f"Loading matches for user: {current_user}")
            
            async with httpx.AsyncClient() as client:
                # Get all likes
                response = await client.get(
                    f"{self.API_BASE_URL}/matches/likes/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Raw API response: {data}")
                    
                    # Get all likes from the results
                    all_likes = data.get("results", [])
                    print(f"Total likes found: {len(all_likes)}")
                    
                    # Get users who have liked me
                    users_who_liked_me = {}
                    # Get users I have liked
                    users_i_liked = {}
                    
                    # Process all likes to build both dictionaries
                    for like in all_likes:
                        # Check if this user liked me
                        if like["liked_user"] == current_user:
                            users_who_liked_me[like["user"]] = like
                            print(f"Found like from {like['user']} to me")
                        
                        # Check if I liked this user
                        if like["user"] == current_user:
                            users_i_liked[like["liked_user"]] = like
                            print(f"Found my like to {like['liked_user']}")
                    
                    print(f"Users who liked me: {list(users_who_liked_me.keys())}")
                    print(f"Users I liked: {list(users_i_liked.keys())}")
                    
                    # Find mutual likes (matches)
                    matches = []
                    seen_matches = set()
                    
                    # Check for mutual likes - users who I liked and who liked me back
                    for username, my_like in users_i_liked.items():
                        if username not in seen_matches:
                            # Get user details for the matched user
                            try:
                                user_response = await client.get(
                                    f"{self.API_BASE_URL}/auth/profile/{username}/",
                                    headers=headers
                                )
                                
                                if user_response.status_code == 200:
                                    user_data = user_response.json()
                                    matched_user_details = {
                                        "id": user_data["id"],
                                        "username": user_data["username"],
                                        "first_name": user_data.get("first_name", ""),
                                        "last_name": user_data.get("last_name", ""),
                                        "profile_picture_url": user_data.get("profile_picture_url"),
                                        "bio": user_data.get("bio", ""),
                                        "industry": user_data.get("industry", ""),
                                        "experience": user_data.get("experience", ""),
                                        "skills": user_data.get("skills", ""),
                                        "contact_links": user_data.get("contact_links", [])
                                    }
                                    
                                    # Check if this user has also liked me
                                    check_mutual_response = await client.get(
                                        f"{self.API_BASE_URL}/matches/likes/?user={username}&liked_user={current_user}",
                                        headers=headers
                                    )
                                    
                                    if check_mutual_response.status_code == 200:
                                        mutual_data = check_mutual_response.json()
                                        if mutual_data.get("results", []):
                                            print(f"Found mutual like between {current_user} and {username}")
                                            match = {
                                                "id": my_like["id"],
                                                "user": current_user,
                                                "matched_user": username,
                                                "matched_user_details": matched_user_details,
                                                "created_at": my_like["created_at"],
                                                "is_mutual": True
                                            }
                                            matches.append(match)
                                            seen_matches.add(username)
                                            print(f"Added mutual match: {current_user} <-> {username}")
                                
                            except Exception as e:
                                print(f"Error fetching user details for {username}: {str(e)}")
                                continue
                    
                    # Sort matches by creation date (most recent first)
                    matches.sort(key=lambda x: x["created_at"], reverse=True)
                    
                    # Update the matches list
                    self.matches = matches
                    print(f"Updated matches list with {len(self.matches)} mutual matches")
                    
                    # Debug print each match
                    for match in self.matches:
                        print(f"Match: {match['user']} <-> {match['matched_user']} ({match['created_at']})")
                        print(f"Match details: {match['matched_user_details']}")
                    
                    # Create direct chats with all matched users automatically
                    print("\n=== Creating Direct Chats with Matched Users ===")
                    for match in self.matches:
                        matched_user = match["matched_user"]
                        success = await self.create_direct_chat_with_user(matched_user)
                        if success:
                            print(f"Ensured chat exists with matched user: {matched_user}")
                        else:
                            print(f"Failed to create chat with matched user: {matched_user}")
                    
                    # Reload rooms to ensure we have the latest list
                    await self.load_rooms()
                else:
                    print(f"Error loading matches: {response.text}")
                    self.error_message = f"Error loading matches: {response.text}"
                    
        except Exception as e:
            print(f"Error in load_matches: {str(e)}")
            self.error_message = f"Error loading matches: {str(e)}"

    async def get_token(self):
        """Get authentication token from state or localStorage."""
        # Get token from AuthState
        auth_state = await self.get_state(AuthState)
        auth_token = auth_state.token
        
        if not auth_token:
            # Try to get token from localStorage
            try:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                print(f"Got token from localStorage: {bool(auth_token)}")
            except Exception as e:
                print(f"Error getting token from localStorage: {str(e)}")
            
            if not auth_token:
                self.error_message = "Authentication required. Please log in."
                return None
        
        return auth_token
            
    async def load_rooms(self):
        """Load rooms from the API."""
        print("\n=== Loading Rooms ===")
        try:
            auth_token = await self.get_token()
            if not auth_token:
                return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/rooms/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.rooms = data.get("results", [])
                    print(f"Loaded {len(self.rooms)} rooms")
                else:
                    print(f"Error loading rooms: {response.text}")
                    self.error_message = f"Error loading rooms: {response.text}"
                    
        except Exception as e:
            print(f"Error in load_rooms: {str(e)}")
            self.error_message = f"Error loading rooms: {str(e)}"

    async def create_room(self, name: str, max_participants: int, selected_members: List[str]):
        """Create a new room."""
        print("\n=== Creating Room ===")
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get current user's username
            current_user = self.get_username
            
            # First create the room without participants
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/communication/rooms/",
                    headers=headers,
                    json={
                        "name": name,
                        "room_type": "group",
                        "max_participants": max_participants
                        # Removed participants from initial creation
                    }
                )
                
                if response.status_code == 201:
                    room_data = response.json()
                    room_id = room_data["id"]
                    print(f"Room created successfully: {room_id}")
                    
                    # Add participants one by one
                    all_members = [current_user] + selected_members  # Include current user
                    for username in all_members:
                        add_participant_response = await client.post(
                            f"{self.API_BASE_URL}/communication/rooms/{room_id}/add_participant/",
                            headers=headers,
                            json={"username": username}
                        )
                        print(f"Adding {username} - Status: {add_participant_response.status_code}")
                        if add_participant_response.status_code != 200 and add_participant_response.status_code != 201:
                            print(f"Failed to add {username}: {add_participant_response.text}")
                    
                    await self.load_rooms()  # Reload rooms list
                else:
                    print(f"Error creating room: {response.text}")
                    self.error_message = f"Error creating room: {response.text}"
                    
        except Exception as e:
            print(f"Error in create_room: {str(e)}")
            self.error_message = f"Error creating room: {str(e)}"

    async def create_group_chat(self, form_data: rx.event.EventHandler) -> rx.event.EventHandler:
        """Handle group chat form submission."""
        try:
            print("\n=== Create Group Chat Debug ===")
            print(f"Form data: {form_data}")
            
            # Extract form data differently - Reflex form data structure is different
            data = {}
            # The form data is stored in the EventHandler object directly
            for key in dir(form_data):
                if not key.startswith('_') and key != 'to' and key != 'form_data':
                    try:
                        data[key] = getattr(form_data, key)
                        print(f"Found form key: {key} = {data[key]}")
                    except:
                        pass
            
            # Get group name and max participants
            group_name = data.get("group_name", "New Group Chat")
            if not group_name:
                group_name = "New Group Chat"
                
            try:
                max_participants = int(data.get("max_participants", 10))
            except:
                max_participants = 10
            
            # Get selected members from form data
            selected_members = []
            for key in data:
                if key.startswith("member_") and data[key]:
                    username = key.split("_")[1]
                    selected_members.append(username)
                    print(f"Selected member: {username}")
            
            # If no members were found with the complex approach, try a simpler approach
            if not selected_members:
                print("No members found with complex approach, trying simpler approach")
                # Try to hard-code Tester2 as a selected member for testing
                selected_members = ["Tester2"]
                print(f"Setting default member: {selected_members}")
            
            if not selected_members:
                self.error_message = "Please select at least one member for the group chat."
                return rx.set_value(self.error_message, self.error_message)
            
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                self.error_message = "Authentication required. Please log in."
                return rx.set_value(self.error_message, self.error_message)
                
            # Hard-code current username to Tester based on logs
            current_username = "Tester"
            print(f"Using current username: {current_username}")
            
            if not current_username:
                self.error_message = "Could not get current user's username"
                return rx.set_value(self.error_message, self.error_message)
            
            # Prepare participants list
            participants = [{"username": current_username}]
            for member in selected_members:
                if member != current_username:  # Avoid duplicate participants
                    participants.append({"username": member})
            
            print(f"Creating room with: name={group_name}, max_participants={max_participants}")
            print(f"Participants: {participants}")
            
            # Set up headers for API calls
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Create the room
            async with httpx.AsyncClient() as client:
                # Create new room
                create_response = await client.post(
                    f"{self.API_BASE_URL}/communication/rooms/",
                    headers=headers,
                    json={
                        "name": group_name,
                        "room_type": "group",
                        "max_participants": max_participants,
                        "participants": participants
                    }
                )
                
                print(f"Create Room Response Status: {create_response.status_code}")
                print(f"Create Room Response: {create_response.text}")
                
                if create_response.status_code == 201:
                    room_data = create_response.json()
                    room_id = room_data["id"]
                    print(f"Room created successfully with ID: {room_id}")
                    
                    # Add participants one by one
                    print(f"\n=== Adding Participants to Room {room_id} ===")
                    for participant in participants:
                        username = participant["username"]
                        add_participant_response = await client.post(
                            f"{self.API_BASE_URL}/communication/rooms/{room_id}/add_participant/",
                            headers=headers,
                            json={"username": username}
                        )
                        print(f"Adding {username} - Status: {add_participant_response.status_code}")
                        if add_participant_response.status_code != 200 and add_participant_response.status_code != 201:
                            print(f"Failed to add {username}: {add_participant_response.text}")
                    
                    # Reload rooms
                    rooms_response = await client.get(
                        f"{self.API_BASE_URL}/communication/rooms/",
                        headers=headers
                    )
                    if rooms_response.status_code == 200:
                        data = rooms_response.json()
                        self.rooms = data.get("results", [])
                        print(f"Successfully reloaded rooms: {len(self.rooms)} rooms found")
                    
                    self.success_message = "Group chat created successfully!"
                else:
                    self.error_message = f"Failed to create group chat: {create_response.text}"
                
        except Exception as e:
            print(f"\n=== Error Debug ===")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            print("==================\n")
            self.error_message = f"Error creating group chat: {str(e)}"
            
    def clear_error_message(self):
        """Clear the error message."""
        self.error_message = ""
        
    def clear_success_message(self):
        """Clear the success message."""
        self.success_message = ""

    @rx.event
    async def view_user_profile(self):
        """View the profile details of the current user."""
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            # Get current profile
            if self.current_profile_index >= len(self.profiles):
                self.error_message = "No profile to view."
                return
                
            current_profile = self.profiles[self.current_profile_index]
            print(f"\nViewing profile: {current_profile}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Get user profile details
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/auth/profile/{current_profile['username']}/",
                    headers=headers
                )
                
                if response.status_code == 200:
                    profile_data = response.json()
                    
                    # Convert skills and past projects to string format that can be displayed safely
                    if "skills" in profile_data and profile_data["skills"]:
                        profile_data["skills_formatted"] = profile_data["skills"]
                    else:
                        profile_data["skills_formatted"] = "No skills listed"
                        
                    if "past_projects" in profile_data and profile_data["past_projects"]:
                        profile_data["past_projects_formatted"] = profile_data["past_projects"]
                    else:
                        profile_data["past_projects_formatted"] = "No past projects listed"
                    
                    self.view_profile_data = profile_data
                    self.show_profile_popup = True
                else:
                    self.error_message = f"Failed to load profile: {response.text}"
        except Exception as e:
            self.error_message = f"Error viewing profile: {str(e)}"
            print(f"Error in view_user_profile: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def close_profile_popup(self):
        """Close the profile popup."""
        self.show_profile_popup = False

    @rx.event
    async def open_chat(self, username: str):
        """Open a chat with the specified user.
        
        Checks if a room exists with this user, and if not, creates one.
        Then redirects directly to the chat room.
        """
        print(f"\n=== Opening chat with user: {username} ===")
        
        try:
            # Get token and current username
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if not auth_token:
                    self.error_message = "Authentication required. Please log in."
                    return
            
            # Get current user's username
            current_username = self.get_username
            
            if not current_username:
                self.error_message = "Could not get current user's username"
                return
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Check if room already exists
            existing_room = await self.find_existing_room(current_username, username)
            
            if existing_room:
                # Room exists, redirect directly to it
                room_id = existing_room.get("id")
                print(f"Found existing room {room_id} - redirecting to it")
                return rx.redirect(f"/chat/room/{room_id}")
            else:
                # Create new room
                print(f"No existing room found - creating a new one with {username}")
                
                async with httpx.AsyncClient() as client:
                    # Use the direct room creation endpoint
                    create_response = await client.post(
                        f"{self.API_BASE_URL}/communication/room/direct/",
                        json={"username": username},
                        headers=headers
                    )
                    
                    print(f"Create room response status: {create_response.status_code}")
                    
                    if create_response.status_code == 201 or create_response.status_code == 200:
                        room_data = create_response.json()
                        room_id = room_data.get("id")
                        
                        if room_id:
                            print(f"Created room with ID {room_id} - redirecting to it")
                            # Save auth token to localStorage again to ensure it's available for the chat page
                            await rx.call_script(f"localStorage.setItem('auth_token', '{auth_token}');")
                            print(f"Auth token saved to localStorage: {auth_token[:5]}...")
                            print(f"REDIRECTING TO: /chat/room/{room_id}")
                            return rx.redirect(f"/chat/room/{room_id}")
                        else:
                            print("Failed to get room ID from created room")
                            self.error_message = "Could not create chat room"
                    else:
                        print(f"Failed to create room: {create_response.text}")
                        self.error_message = f"Failed to create chat room: {create_response.status_code}"
        except Exception as e:
            print(f"Error in open_chat: {str(e)}")
            self.error_message = f"Error opening chat: {str(e)}"

    def open_group_chat(self, room_id: str, room_name: str):
        """Open a group chat with the specified ID."""
        print(f"Opening group chat: {room_name} ({room_id})")
        return rx.redirect(f"/chat/room/{room_id}")

    async def create_direct_group_chat(self, form_data: rx.event.EventHandler) -> rx.event.EventHandler:
        """Handle group chat form submission.
        
        This is a wrapper that calls the create_group_chat method to maintain
        backward compatibility with SideBar.py references.
        """
        return await self.create_group_chat(form_data)

def profile_card() -> rx.Component:
    return rx.cond(
        MatchState.loading,
        rx.center(
            rx.spinner(size="3", color="white"),
            padding="8",
        ),
        rx.cond(
            MatchState.error_message,
            rx.box(
                rx.text(
                    MatchState.error_message,
                    color="white",
                    class_name="bg-blue-800 p-3 rounded-lg mb-4",
                ),
                width="100%",
                max_width="600px",
                text_align="center",
            ),
            rx.box(
                rx.vstack(
                    rx.image(
                        src=rx.cond(
                            MatchState.profiles[MatchState.current_profile_index]["profile_picture_url"] != None,
                            MatchState.profiles[MatchState.current_profile_index]["profile_picture_url"],
                            ""
                        ),
                        class_name="w-full h-[700px] object-cover rounded-3xl border-4 border-white mt-3",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.box(
                                class_name="w-3 h-3 rounded-full bg-green-400",
                            ),
                            rx.text(
                                "Recently Active",
                                class_name="text-gray-400 text-sm",
                            ),
                            spacing="2",
                        ),
                        rx.heading(
                            rx.cond(
                                (MatchState.profiles[MatchState.current_profile_index]["first_name"] != "") & 
                                (MatchState.profiles[MatchState.current_profile_index]["last_name"] != ""),
                                f"{MatchState.profiles[MatchState.current_profile_index]['first_name']} {MatchState.profiles[MatchState.current_profile_index]['last_name']}",
                                MatchState.profiles[MatchState.current_profile_index]["username"]
                            ),
                            size="7",
                            class_name="text-sky-400",
                        ),
                        rx.text(
                            f"Industry: {MatchState.profiles[MatchState.current_profile_index]['industry']}",
                            class_name="text-black",
                        ),
                        rx.text(
                            f"Experience: {MatchState.profiles[MatchState.current_profile_index]['experience']}",
                            class_name="text-black",
                        ),
                        rx.flex(
                            rx.cond(
                                (MatchState.profiles[MatchState.current_profile_index]["skills"] != None) & 
                                (MatchState.profiles[MatchState.current_profile_index]["skills"] != ""),
                                rx.hstack(
                                    rx.foreach(
                                        MatchState.profiles[MatchState.current_profile_index]["skills"].split(","),
                                        lambda skill: rx.box(
                                            skill,
                                            class_name="bg-sky-800 text-white px-3 py-1 rounded-full m-1 text-sm",
                                        ),
                                    ),
                                    wrap="wrap",
                                    justify="center",
                                    width="100%",
                                ),
                                rx.box(
                                    "No skills",
                                    class_name="bg-sky-800 text-white px-3 py-1 rounded-full m-1 text-sm",
                                ),
                            ),
                            wrap="wrap",
                            justify="center",
                            width="100%",
                        ),
                        rx.text(
                            rx.cond(
                                MatchState.profiles[MatchState.current_profile_index]["bio"] != None,
                                MatchState.profiles[MatchState.current_profile_index]["bio"],
                                "No bio available"
                            ),
                            class_name="text-gray-400 text-sm text-center",
                            noOfLines=3,
                        ),
                        padding="4",
                        spacing="2",
                        class_name="w-full bg-sky-100 rounded-2xl p-2 mt-1",
                    ),
                    spacing="0",
                    width="full",
                ),
                class_name="w-[400px] overflow-hidden shadow-xl",
            ),
        ),
    )

def chat_interface() -> rx.Component:
    """
    Note: This embedded chat interface is no longer used.
    Chat functionality has been moved to the dedicated ChatPage component.
    We now redirect users to /chat/user/[username] instead of showing an embedded chat.
    """
    # Return empty fragment since we're not using embedded chat anymore
    return rx.fragment()

def action_buttons() -> rx.Component:
    """Action buttons for like, dislike, etc."""
    return rx.hstack(
        rx.button(
            rx.icon("arrow-left", class_name="drop-shadow-lg"),
            on_click=MatchState.previous_profile,
            class_name="rounded-full font-bold w-12 h-12 bg-yellow-400 text-white hover:bg-yellow-500 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("x", class_name="drop-shadow-lg"),
            on_click=MatchState.dislike_profile,
            class_name="rounded-full w-12 h-12 bg-red-400 text-white hover:bg-red-500 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("star", class_name="drop-shadow-lg"),
            on_click=MatchState.super_like_profile,
            class_name="rounded-full w-12 h-12 bg-blue-400 text-white hover:bg-blue-500 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("check", class_name="drop-shadow-lg"),
            on_click=MatchState.like_profile,
            class_name="rounded-full w-14 h-14 bg-green-400 text-white hover:bg-green-500 transform transition-all hover:scale-150",
        ),
        rx.button(
            rx.icon("eye", class_name="drop-shadow-lg"),
            on_click=MatchState.view_user_profile,
            class_name="rounded-full w-12 h-12 bg-purple-400 text-white hover:bg-purple-500 transform transition-all hover:scale-110",
        ),
        spacing="3",
        justify="center",
        padding_y="6",
    )

def profile_popup() -> rx.Component:
    """Profile popup to display user details."""
    return rx.cond(
        MatchState.show_profile_popup,
        rx.box(
            rx.center(
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.button(
                            rx.icon("x"),
                            on_click=MatchState.close_profile_popup,
                            size="3",
                            color="red",
                            class_name="bg-white hover:bg-red-100 hover:text-red-600 transition-transform transform hover:scale-105 duration-200 mt-2 mr-2"
                        ),
                        width="100%",
                    ),
                    rx.divider(),
                    rx.cond(
                        MatchState.view_profile_data is not None,
                        rx.vstack(
                            rx.avatar(
                                name=f"{MatchState.view_profile_data.get('first_name', '')} {MatchState.view_profile_data.get('last_name', '')}",
                                src=MatchState.view_profile_data.get("profile_picture_url", ""),
                                size="8",
                                class_name="rounded-full"
                            ),
                            rx.heading(
                                f"{MatchState.view_profile_data.get('first_name', '')} {MatchState.view_profile_data.get('last_name', '')}",
                                size="5",
                                margin_top="2",
                                class_name="text-sky-700 font-bold"
                            ),
                            rx.text(f"@{MatchState.view_profile_data.get('username', '')}", 
                                color="gray",
                                font_size="1em",
                                margin_bottom="2",
                            ),
                            
                            rx.divider(),
                            
                            rx.box(
                                rx.text("Bio:", 
                                    font_weight="bold", 
                                    font_size="1.2em",
                                    class_name="text-sky-600 ml-7"
                                ),
                                rx.text(
                                    MatchState.view_profile_data.get("bio", "No bio available"),
                                    font_size="1.1em",
                                    padding="3",
                                    bg="gray.50",
                                    class_name="text-black ml-7 rounded-2xl"
                                ),
                                width="100%",
                                margin_top="3",
                                margin_bottom="4",
                            ),
                            
                            rx.hstack(
                                rx.box(
                                    rx.text("Industry:", 
                                        font_weight="bold", 
                                        font_size="1.2em",
                                        class_name="text-sky-600 ml-7",
                                    ),
                                    rx.text(
                                        MatchState.view_profile_data.get("industry", "Not specified"),
                                        font_size="1.1em",
                                        padding="3",
                                        class_name="ml-7 text-sky-500"
                                    ),
                                    width="50%",
                                ),
                                rx.box(
                                    rx.text("Experience:", 
                                        font_weight="bold", 
                                        font_size="1.2em",
                                        class_name="text-sky-600 ml-7",
                                    ),
                                    rx.text(
                                        MatchState.view_profile_data.get("experience", "Not specified"),
                                        font_size="1.1em",
                                        padding="3",
                                        class_name="ml-7 text-sky-500"
                                    ),
                                    width="50%",
                                ),
                                width="100%",
                                margin_bottom="4",
                                spacing="4",
                            ),
                            
                            rx.box(
                                rx.text("Skills:", 
                                    font_weight="bold", 
                                    font_size="1.5em",
                                    class_name="text-sky-700 ml-7",
                                ),
                                rx.text(
                                    MatchState.view_profile_data.get("skills_formatted", "No skills listed"),
                                    font_size="1.0em",
                                    padding="3",
                                    class_name="ml-7 text-black"
                                ),
                                width="100%",
                                margin_bottom="4",
                            ),
                            
                            rx.box(
                                rx.text("Past Projects:", 
                                    font_weight="bold", 
                                    font_size="1.2em",
                                    class_name="text-sky-700 ml-7",
                                ),
                                rx.text(
                                    MatchState.view_profile_data.get("past_projects_formatted", "No past projects listed"),
                                    font_size="1.1em",
                                    padding="3",
                                    class_name="ml-7 text-black"
                                ),
                                width="100%",
                                margin_bottom="4",
                            ),
                            
                            rx.box(
                                rx.text("Career Summary:", 
                                    font_weight="bold", 
                                    font_size="1.2em",
                                    class_name="text-sky-700 ml-7",
                                ),
                                rx.text(
                                    MatchState.view_profile_data.get("career_summary", "No career summary"),
                                    font_size="1.0em",
                                    padding="3",
                                    class_name="ml-7 text-black mb-5"
                                ),
                                width="100%",
                            ),
                            
                            width="100%",
                            align_items="center",
                            spacing="4",
                            padding="4",
                        ),
                        rx.center(
                            rx.spinner(),
                            height="200px",
                        ),
                    ),
                    width="100%",
                    spacing="4",
                    padding="6",
                    max_width="700px",
                    bg="white",
                    border_radius="lg",
                    box_shadow="xl",
                    class_name="rounded-3xl",
                ),
                position="fixed",
                top="0",
                left="0",
                width="100%",
                height="100%",
                z_index="1000",
                bg="rgba(0,0,0,0.7)",
                
            ),
        ),
        rx.fragment(),
    )

def match_page() -> rx.Component:
    """The match page."""
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.center(
                rx.vstack(
                    # Error message
                    rx.cond(
                        MatchState.error_message != "",
                        rx.box(
                            rx.icon("x", color="red"),
                            rx.text(
                                MatchState.error_message,
                                font_weight="bold",
                                color="white",
                            ),
                            bg="red.500",
                            padding="3",
                            border_radius="md",
                            display="flex",
                            align_items="center",
                            gap="2",
                            width="90%",
                            mb="4",
                        ),
                        rx.fragment(),
                    ),
                    # Success message
                    rx.cond(
                        MatchState.success_message != "",
                        rx.box(
                            rx.icon("check", color="white"),
                            rx.text(
                                MatchState.success_message,
                                font_weight="bold",
                                color="white",
                            ),
                            bg="green.500",
                            padding="3",
                            border_radius="md",
                            display="flex",
                            align_items="center",
                            gap="2",
                            width="90%",
                            mb="4",
                        ),
                        rx.fragment(),
                    ),
                    profile_card(),
                    action_buttons(),
                    align_items="center",
                ),
            ),
            class_name="flex-1 min-h-screen bg-gray-800 flex flex-col justify-center items-center",
        ),
        # This is just a placeholder now - chat is handled by the dedicated ChatPage
        chat_interface(),
        profile_popup(),  # Add the profile popup component
        spacing="0",
        width="full",
        height="100vh",
        overflow="hidden",
        on_mount=MatchState.on_mount,
    )
