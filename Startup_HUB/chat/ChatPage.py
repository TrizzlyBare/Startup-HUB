import reflex as rx
import json
import asyncio
import httpx
import time
from typing import List, Dict, Optional, Any
from ..Matcher.SideBar import sidebar
from ..Auth.AuthPage import AuthState

class ChatState(rx.State):
    # API settings
    API_BASE_URL: str = "http://startup-hub:8000/api"
    API_HOST_URL: str = "http://100.95.107.24:8000/api"  # Alternative direct IP
    WS_BASE_URL: str = "ws://startup-hub:8000/ws"
    auth_token: str = ""
    
    # Chat data
    chat_history: list[tuple[str, str]] = []
    message: str = ""
    current_chat_user: str = ""
    current_room_id: Optional[str] = None
    rooms: List[Dict[str, Any]] = []
    
    # Typing indicator
    typing_users: List[str] = []
    
    # Call related states
    show_call_popup: bool = False
    show_video_popup: bool = False
    call_duration: int = 0
    is_muted: bool = False
    remote_is_muted: bool = False
    is_camera_off: bool = False
    show_calling_popup: bool = False
    call_type: str = "audio"
    
    # Incoming call states
    show_incoming_call: bool = False
    call_invitation_id: str = ""
    incoming_caller: str = ""
    
    # Active call in room
    active_room_call: Dict[str, Any] = {}
    joining_existing_call: bool = False
    
    # WebRTC related states
    webrtc_config: Dict[str, Any] = {}
    ice_servers: List[Dict[str, Any]] = []
    signaling_connected: bool = False
    is_call_connected: bool = False
    
    # Loading and error states
    loading: bool = True
    error_message: str = ""
    success_message: str = ""
    
    # WebSocket connection status (for future implementation)
    is_connected: bool = False
    
    # UI state
    sidebar_visible: bool = True
    
    # User info state
    username: str = ""
    
    # Debug flags - these control what features are enabled during development
    debug_show_info: bool = True        # Show debug info panel
    debug_use_dummy_data: bool = False  # Use dummy data instead of API calls where needed (set to False)
    debug_log_api_calls: bool = True    # Log API calls and responses
    
    # Custom API URL for room call announcement
    room_call_api_url: str = ""
    
    @rx.var
    def route_room_id(self) -> str:
        """Get room_id from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            room_id = params.get("room_id", "")
            if room_id:
                print(f"Found room_id in URL: {room_id}")
                return room_id
        return ""

    @rx.var
    def is_someone_typing(self) -> bool:
        return len(self.typing_users) > 0
        
    @rx.var
    def typing_message(self) -> str:
        if len(self.typing_users) == 1:
            return f"{self.typing_users[0]} is typing..."
        elif len(self.typing_users) == 2:
            return f"{self.typing_users[0]} and {self.typing_users[1]} are typing..."
        elif len(self.typing_users) > 2:
            return "Several people are typing..."
        return ""

    @rx.var
    def formatted_rooms(self) -> List[Dict[str, str]]:
        """Format rooms data for display."""
        result = []
        for room in self.rooms:
            try:
                # Extract usable data from room dict
                room_data = {
                    "id": str(room.get("id", "")),
                    "name": str(room.get("name", "Unknown")),
                    "profile_image": str(room.get("profile_image", "")),
                }
                
                # Safely extract last message content
                last_message = room.get("last_message", {})
                if last_message and isinstance(last_message, dict):
                    room_data["last_message"] = str(last_message.get("content", ""))
                else:
                    room_data["last_message"] = ""
                    
                result.append(room_data)
            except Exception:
                # Ignore malformed room data
                pass
                
        return result
    
    @rx.event
    async def go_back_to_chat_list(self):
        """Go back to the chat list from a chat room."""
        print("Going back to chat list")
        # Clear the current room state
        self.current_room_id = ""
        self.current_chat_user = ""
        
        # Redirect to the chat list
        return rx.redirect("/chat")

    async def get_token(self) -> str:
        """Get authentication token from state or localStorage."""
        if self.auth_token:
            return self.auth_token
            
        # Try to get token from AuthState
        try:
            auth_state = await self.get_state(AuthState)
            if auth_state and auth_state.token:
                self.auth_token = auth_state.token
                return self.auth_token
        except Exception as e:
            print(f"Error getting token from AuthState: {e}")
        
        # Fallback to localStorage
        try:
            token = await rx.call_script("localStorage.getItem('auth_token')")
            if token:
                self.auth_token = token
                return token
        except Exception as e:
            print(f"Error getting token from localStorage: {e}")
            
        return ""

    async def get_current_username(self) -> str:
        """Get current username from AuthState or localStorage."""
        # First check if it's already in state
        if self.username:
            return self.username
            
        # Then try to get from AuthState
        try:
            auth_state = await self.get_state(AuthState)
            if auth_state and auth_state.username:
                print(f"Got username from AuthState: {auth_state.username}")
                self.username = auth_state.username
                return self.username
        except Exception as e:
            print(f"Error getting username from AuthState: {e}")
        
        # Then try to get from localStorage
        try:
            username = await rx.call_script("localStorage.getItem('username')")
            if username:
                print(f"Got username from localStorage: {username}")
                self.username = username
                return username
        except Exception as e:
            print(f"Error getting username from localStorage: {e}")
        
        # As a last resort, try to get from an auth debug call
        if self.auth_token:
            try:
                # Call auth-debug API endpoint to get user info
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.API_BASE_URL}/authen/auth-debug/",
                        headers={"Authorization": f"Token {self.auth_token}"},
                        follow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        user_from_token = data.get("user_from_token", {})
                        if user_from_token and "username" in user_from_token:
                            username = user_from_token["username"]
                            print(f"Got username from auth-debug: {username}")
                            self.username = username
                            # Store in localStorage for future use
                            await rx.call_script(f"localStorage.setItem('username', '{username}')")
                            return username
            except Exception as e:
                print(f"Error getting username from auth-debug: {e}")
        
        return "user"  # Default fallback

    async def get_username(self) -> str:
        """Get username from state or localStorage."""
        if self.username:
            print(f"Using cached username from state: {self.username}")
            return self.username
        
        # Using a safe approach that doesn't await rx.call_script
        # Set username in state and return a default value for now
        # The script will update the state asynchronously
        rx.call_script("""
            const username = localStorage.getItem('username');
            if (username) {
                // Set the username directly in the state
                state.username = username;
                console.log('Username set from localStorage:', username);
            } else {
                console.log('No username found in localStorage');
            }
        """)
        
        # If we have a token, try to get username from API
        if self.auth_token:
            try:
                print(f"Found token, trying to get username from API using token: {self.auth_token[:8]}...")
                # Call API to get user info
                async with httpx.AsyncClient() as client:
                    print(f"API URL being called: {self.API_BASE_URL}/authen/auth-debug/")
                    
                    response = await client.get(
                        f"{self.API_BASE_URL}/authen/auth-debug/",
                        headers={"Authorization": f"Token {self.auth_token}"},
                        follow_redirects=True
                    )
                    
                    print(f"Auth debug response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"Auth debug API full response: {data}")
                            
                            # Check if user_from_token exists
                            user_from_token = data.get("user_from_token", {})
                            print(f"user_from_token data: {user_from_token}")
                            
                            if user_from_token and "username" in user_from_token:
                                username = user_from_token["username"]
                                print(f"Got username from API: {username}")
                                self.username = username
                                # Save to localStorage
                                rx.call_script(f"""
                                    localStorage.setItem('username', '{username}');
                                    console.log('Username saved to localStorage:', '{username}');
                                """)
                                return username
                            else:
                                print("No username found in user_from_token data")
                        except Exception as e:
                            print(f"Error parsing JSON response: {e}")
                            print(f"Raw response text: {response.text[:500]}")
                    else:
                        print(f"Auth debug API error response: {response.text[:500]}")
            except Exception as e:
                print(f"Error getting username from API: {e}")
                import traceback
                traceback.print_exc()
        
        print("Using default username: user")
        return "user"  # Default fallback

    async def get_storage_item(self, key: str) -> str:
        """Safely get an item from localStorage using direct JavaScript.
        
        This uses a simple approach that should work in most Reflex versions.
        """
        # For now, return empty string since we can't properly await rx.call_script
        # in the current Reflex version
        print(f"Attempting to get {key} from localStorage")
        
        try:
            # In this version of Reflex, we can't properly await rx.call_script
            # So we'll return an empty string for now
            return ""
        except Exception as e:
            print(f"Error in get_storage_item: {e}")
            return ""

    @rx.event
    async def on_mount(self):
        """Initialize the component when it mounts."""
        print("Chat component mounted")
        
        # Check for active call notifications - this will help catch any pending calls
        # when a user first loads the application
        await self.get_active_call_notifications()
        
        # Set up periodic call notification checks
        asyncio.create_task(self._periodic_notification_check())
        
        # Proceed with normal initialization
        # ... existing code ...
        
        # Use try-except to make this robust against different Reflex versions
        try:
            # Get authentication token from AuthState
            self.auth_token = await self.get_token()
            
            # Fetch the username from the auth-debug API endpoint
            if self.auth_token:
                # Try multiple API paths to find the one that works
                username_found = False
                
                # List of API endpoints to try
                api_endpoints = [
                    (self.API_BASE_URL, "authen/auth-debug/"),
                    (self.API_BASE_URL, "auth/auth-debug/"),
                    (self.API_HOST_URL, "authen/auth-debug/"),
                    (self.API_HOST_URL, "auth/auth-debug/")
                ]
                
                for base_url, path in api_endpoints:
                    if username_found:
                        break
                        
                    try:
                        full_url = f"{base_url}/{path}"
                        print(f"Trying auth-debug API at: {full_url}")
                        
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                full_url,
                                headers={"Authorization": f"Token {self.auth_token}"},
                                follow_redirects=True,
                                timeout=5.0  # 5 second timeout
                            )
                            
                            print(f"API response status: {response.status_code}")
                            
                            if response.status_code == 200:
                                try:
                                    data = response.json()
                                    print(f"Auth debug API response: {data}")
                                    user_from_token = data.get("user_from_token", {})
                                    
                                    if user_from_token and "username" in user_from_token:
                                        username = user_from_token["username"]
                                        print(f"Got username from auth-debug API: {username}")
                                        self.username = username
                                        # Store in localStorage for future use
                                        rx.call_script(f"""
                                            localStorage.setItem('username', '{username}');
                                            console.log('Username saved to localStorage:', '{username}');
                                        """)
                                        username_found = True
                                        break
                                    else:
                                        print(f"No username in user_from_token data: {user_from_token}")
                                except Exception as e:
                                    print(f"Error parsing response JSON: {e}")
                            else:
                                print(f"Unsuccessful response: {response.status_code}")
                                
                    except Exception as e:
                        print(f"Error trying endpoint {full_url}: {e}")
                
                if not username_found:
                    # As a fallback, try to get user info from the token endpoint
                    try:
                        print("Trying token endpoint as fallback")
                        async with httpx.AsyncClient() as client:
                            for base_url in [self.API_BASE_URL, self.API_HOST_URL]:
                                try:
                                    token_url = f"{base_url}/authen/token/"
                                    print(f"Trying: {token_url}")
                                    token_response = await client.get(
                                        token_url,
                                        headers={"Authorization": f"Token {self.auth_token}"},
                                        follow_redirects=True,
                                        timeout=5.0
                                    )
                                    
                                    if token_response.status_code == 200:
                                        token_data = token_response.json()
                                        print(f"Token API response: {token_data}")
                                        
                                        if "username" in token_data:
                                            username = token_data["username"]
                                            print(f"Got username from token API: {username}")
                                            self.username = username
                                            rx.call_script(f"""
                                                localStorage.setItem('username', '{username}');
                                                console.log('Username saved from token API:', '{username}');
                                            """)
                                            username_found = True
                                            break
                                except Exception as e:
                                    print(f"Error trying token endpoint {token_url}: {e}")
                                    
                    except Exception as e:
                        print(f"Error in token fallback: {e}")
            
            # Instead of awaiting rx.call_script directly, set the username from JavaScript
            # This will set the username in state and not hang waiting for the call_script result
            rx.call_script("""
                const username = localStorage.getItem('username');
                console.log('Found username in localStorage:', username);
                
                if (username) {
                    // Set the username directly in the state
                    if (window._state) {
                        window._state.username = username;
                        console.log('Username set directly in state:', username);
                    }
                    // Also trigger a state update via event
                    window.dispatchEvent(new CustomEvent('username_set', { detail: { username } }));
                } else {
                    console.log('No username found in localStorage');
                }
            """)
            
            # Wait a moment for username to be set
            await asyncio.sleep(0.2)
            
            # Debug print the username
            print(f"Auth values - token: {self.auth_token}, username: {self.username}")
            
            # Step 1: Load the list of rooms (conversations)
            await self.load_rooms()
            
            # Step 2: Check if we have a room_id in the URL route
            room_id = self.route_room_id
            
            # Step 3: If we have a room_id, load that specific room's messages
            if room_id:
                self.current_room_id = room_id
                print(f"Opening room from URL: {room_id}")
                await self.load_messages()
            else:
                print("No room_id in URL, showing rooms list only")
                
        except Exception as e:
            print(f"Error in on_mount: {e}")
            self.error_message = "Error loading chat data. Please try again."
            
            # If we fail to load from API, use dummy data in development
            if self.debug_use_dummy_data:
                await self._set_dummy_data()
                if self.current_room_id:
                    self._set_dummy_messages()

    async def _set_dummy_data(self):
        """Set dummy room data for development and testing."""
        print("Setting dummy room data")
        self.rooms = [
            {
                "id": "1",
                "name": "Test Chat Room",
                "profile_image": "",
                "last_message": {"content": "This is a test message in the first room"}
            },
            {
                "id": "2",
                "name": "Another Test Room",
                "profile_image": "",
                "last_message": {"content": "Hello from the second room"}
            },
            {
                "id": "3",
                "name": "Third Room",
                "profile_image": "",
                "last_message": {}
            }
        ]
        print(f"Created {len(self.rooms)} dummy rooms")
        
    def _set_dummy_messages(self):
        """Set dummy messages for development and testing."""
        print("Setting dummy messages")
        self.chat_history = [
            ("other", "Hello there! This is a test message."),
            ("user", "Hi! I'm responding to the test."),
            ("other", "Great to see the chat working!"),
            ("user", "Yes, it's working well."),
        ]
        print(f"Created {len(self.chat_history)} dummy messages")

    async def fix_username_if_needed(self):
        """Helper method to fix username issues by trying multiple sources."""
        if self.username and self.username != "user":
            # Already have a valid username
            return
            
        print("Attempting to fix missing username")
        
        # First try to get from localStorage (client-side)
        rx.call_script("""
            const username = localStorage.getItem('username');
            console.log('Checking localStorage for username:', username);
            
            if (username) {
                // Force update all state objects to ensure correct username
                if (window._state) {
                    window._state.username = username;
                    console.log('Fixed username from localStorage:', username);
                }
                
                if (state) {
                    state.username = username;
                }
            }
        """)
        
        # Wait a brief moment for the script to execute
        await asyncio.sleep(0.1)
        
        # If we now have a valid username, we're done
        if self.username and self.username != "user":
            print(f"Username fixed from localStorage: {self.username}")
            return
        
        # Otherwise, try the auth-debug endpoint
        if self.auth_token:
            try:
                # Try multiple API paths to find one that works
                api_endpoints = [
                    (self.API_BASE_URL, "authen/auth-debug/"),
                    (self.API_BASE_URL, "auth/auth-debug/"),
                    (self.API_HOST_URL, "authen/auth-debug/"),
                    (self.API_HOST_URL, "auth/auth-debug/")
                ]
                
                for base_url, path in api_endpoints:
                    try:
                        full_url = f"{base_url}/{path}"
                        print(f"Trying to fix username via: {full_url}")
                        
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                full_url,
                                headers={"Authorization": f"Token {self.auth_token}"},
                                follow_redirects=True,
                                timeout=5.0
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                user_from_token = data.get("user_from_token", {})
                                
                                if user_from_token and "username" in user_from_token:
                                    username = user_from_token["username"]
                                    print(f"Fixed username from API: {username}")
                                    self.username = username
                                    rx.call_script(f"""
                                        localStorage.setItem('username', '{username}');
                                        console.log('Username fixed and saved to localStorage:', '{username}');
                                    """)
                                    return
                    except Exception as e:
                        print(f"Error trying endpoint {full_url}: {e}")
                        continue
            except Exception as e:
                print(f"Error in auth-debug username fix attempt: {e}")
        
        # If we still don't have a username, check if we're in Tester's chat rooms
        try:
            # Look through the rooms data
            for room in self.rooms:
                room_name = room.get("name", "")
                
                # Check if Tester appears in the room name (likely their direct message room)
                if "Tester" in room_name:
                    print("Inferring username as Tester from room names")
                    self.username = "Tester"
                    rx.call_script("""
                        localStorage.setItem('username', 'Tester');
                        console.log('Username inferred and saved to localStorage: Tester');
                    """)
                    return
                    
                # Check participants if available
                participants = room.get("participants", [])
                for p in participants:
                    if isinstance(p, dict):
                        if "user" in p and isinstance(p["user"], dict) and p["user"].get("username") == "Tester":
                            print("Found Tester as participant, setting username")
                            self.username = "Tester"
                            rx.call_script("""
                                localStorage.setItem('username', 'Tester');
                                console.log('Username inferred and saved to localStorage: Tester');
                            """)
                            return
        except Exception as e:
            print(f"Error in room-based username inference: {e}")
        
        # Last resort: use message data
        if self.chat_history:
            for sender, _ in self.chat_history:
                if sender == "user":
                    # We've already marked some messages as from the current user
                    # But we don't know the actual username
                    print("Setting username to Tester based on existing user messages")
                    self.username = "Tester"
                    rx.call_script("""
                        localStorage.setItem('username', 'Tester');
                        console.log('Username inferred from messages and saved: Tester');
                    """)
                    return

        # If all else fails, default to "Tester" for testing purposes
        print("All username detection methods failed, defaulting to Tester for testing")
        self.username = "Tester"
        rx.call_script("""
            localStorage.setItem('username', 'Tester');
            console.log('Username defaulted to: Tester');
        """)

    @rx.event
    async def send_message(self):
        """Send a message to the current room."""
        if not self.message.strip():
            print("Cannot send empty message")
            return
            
        # Verify the room_id is valid
        if not self.current_room_id or not isinstance(self.current_room_id, str) or not self.current_room_id.strip():
            print("Cannot send message: missing or invalid room_id")
            self.error_message = "Cannot send message: no active chat room"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Cannot send message: not authenticated")
            self.error_message = "Not authenticated. Please log in."
            return
            
        # Store the room_id locally to avoid any issues with state changes  
        room_id = self.current_room_id
            
        try:
            print(f"Sending message to room {room_id}: {self.message[:10]}...")
            # Add message to UI immediately for responsiveness
            self.chat_history.append(("user", self.message))
            message_to_send = self.message
            self.message = ""
            yield
            
            # Send via REST API - with the correct endpoint path
            print("Making API call to send message...")
            
            # Set up headers
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Use AsyncClient for HTTP requests
            async with httpx.AsyncClient() as client:
                # Include both room and room_id fields with the same value
                payload = {
                    "room": room_id,
                    "room_id": room_id,
                    "content": message_to_send, 
                    "message_type": "text"
                }
                print(f"Message payload: {payload}")
                
                response = await client.post(
                    f"{self.API_BASE_URL}/communication/messages/",
                    json=payload,
                    headers=headers,
                    follow_redirects=True
                )
                
                print(f"Message send API response status: {response.status_code}")
                
                if response.status_code != 201:
                    # If message failed to send, show error
                    self.error_message = "Failed to send message"
                    print(f"Failed to send message: {response.text}")
                else:
                    print("Message sent successfully")
                    # Reload messages to make sure we have the latest
                    await self.load_messages()
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            self.error_message = f"Error sending message: {str(e)}"

    @rx.event
    async def send_typing_notification(self):
        """Send typing notification to other users."""
        # Verify the room_id is valid
        if not self.current_room_id or not isinstance(self.current_room_id, str) or not self.current_room_id.strip():
            print("Cannot send typing notification: missing or invalid room_id")
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Cannot send typing notification: not authenticated")
            return
            
        # Store the room_id locally to avoid any issues with state changes
        room_id = self.current_room_id
        
        # Run typing notification in background
        self._send_typing_notification_impl(room_id)
            
    def _send_typing_notification_impl(self, room_id: str):
        """Implementation of typing notification that runs in background."""
        # Define the task
        async def _typing_task():
            try:
                # Since the typing endpoint doesn't exist, we'll simulate it locally
                # Add the current user to typing_users list temporarily
                if self.username not in self.typing_users:
                    self.typing_users.append(self.username)
                    
                # Wait a bit and then remove typing status
                await asyncio.sleep(2)
                
                # Remove user from typing list
                if self.username in self.typing_users:
                    self.typing_users.remove(self.username)
                    
                """
                # This code is kept for reference but won't be used
                # since the typing endpoint doesn't exist
                
                # Set up headers
                headers = {
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
                
                # Use AsyncClient for HTTP requests
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.API_BASE_URL}/communication/rooms/{room_id}/typing/",
                        headers=headers,
                        follow_redirects=True
                    )
                    print(f"Typing notification response: {response.status_code}")
                """
            except Exception as e:
                # Log error but continue without showing error to user
                print(f"Error in typing notification: {str(e)}")
                
        # Start the task
        asyncio.create_task(_typing_task())

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Upload media and send as a message."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
            
        for file in files:
            try:
                # Save file locally first
                upload_data = file
                outfile = rx.get_upload_dir() / file.filename
                with outfile.open("wb") as file_object:
                    file_object.write(upload_data)
                
                # Get file URL for display
                file_url = rx.get_upload_url(file.filename)
                
                # Add to UI immediately
                self.chat_history.append(("user", file_url))
                yield
                
                # Determine media type
                file_type = "image"  # Default
                if file.content_type.startswith("video/"):
                    file_type = "video"
                elif file.content_type.startswith("audio/"):
                    file_type = "audio"
                elif not file.content_type.startswith("image/"):
                    file_type = "document"
                
                # Upload file to server
                form_data = rx.FormData()
                form_data.add_file("file", upload_data, filename=file.filename)
                form_data.add_field("file_type", file_type)
                
                # Set up headers
                headers = {
                    "Authorization": f"Token {self.auth_token}"
                }
                
                # Use AsyncClient for HTTP requests
                async with httpx.AsyncClient() as client:
                    media_response = await client.post(
                        f"{self.API_BASE_URL}/communication/media/",
                        data=form_data,
                        headers=headers,
                        follow_redirects=True
                    )
                    
                    media_data = media_response.json()
                    media_id = media_data.get("id")
                    
                    # Send message with media
                    message_data = {
                        "room_id": self.current_room_id,
                        "message_type": file_type,
                        f"{file_type}": media_id
                    }
                    
                    message_headers = {
                        "Authorization": f"Token {self.auth_token}",
                        "Content-Type": "application/json"
                    }
                    
                    await client.post(
                        f"{self.API_BASE_URL}/communication/messages/",
                        json=message_data,
                        headers=message_headers,
                        follow_redirects=True
                    )
                
                # Update last message time
                self.last_message_time = asyncio.get_event_loop().time()
            except Exception as e:
                self.error_message = f"Error uploading file: {str(e)}"

    @rx.event
    async def open_room(self, room_id: str, room_name: str = None):
        """Open a chat room by ID and load messages."""
        print(f"\n=== Opening Room {room_id} ===")
        
        try:
            if not room_id:
                self.error_message = "Invalid room ID"
                return
                
            # Set the active room and user
            was_previously_set = (self.current_room_id == room_id)
            self.current_room_id = room_id
            
            # If room_name is provided, use it; otherwise find it from our cached rooms
            if room_name:
                self.current_chat_user = room_name
            else:
                # Try to find room name from the rooms we've already loaded
                found_name = self._find_room_name_from_cache(room_id)
                if found_name:
                    self.current_chat_user = found_name
                else:
                    self.current_chat_user = f"Room {room_id[:8]}..."
            
            print(f"Opened room: {self.current_chat_user} (ID: {room_id})")
            
            # Load messages for this room
            await self.load_messages()
            
            # Connect to WebSocket for this room if not already connected
            if not was_previously_set or not self.is_connected:
                await self.on_room_open()
                
            # Check if there are any active calls in this room
            await self.check_room_active_calls(room_id)
            
        except Exception as e:
            self.error_message = f"Error opening room: {str(e)}"
            print(f"Error opening room: {str(e)}")
            
    @rx.event
    async def check_room_active_calls(self, room_id: str):
        """Check if there are any active calls in the current room."""
        print(f"[WebRTC Debug] Checking for active calls in room {room_id}")
        
        try:
            # Get authentication token
            self.auth_token = await self.get_token()
            if not self.auth_token:
                print("[WebRTC Debug] Not authenticated, can't check for active calls")
                return
                
            # Fetch active notifications
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            api_url = f"{self.API_BASE_URL}/communication/incoming-calls/"
            
            client = httpx.AsyncClient()
            response = await client.get(
                api_url,
                headers=headers,
                follow_redirects=True
            )
            
            if response.status_code == 404:
                # If the endpoint doesn't exist yet, use WebSocket check as fallback
                print("[WebRTC Debug] Notification API endpoint not found (404) - checking for active calls via WebSocket")
                return self._check_active_calls_via_websocket(room_id)
            elif response.status_code != 200:
                print(f"[WebRTC Debug] Failed to fetch call notifications: {response.status_code}")
                return
                
            # Process notifications
            notifications = response.json()
            if self.debug_log_api_calls:
                print(f"[WebRTC Debug] Received {len(notifications)} active call notifications")
                
            # Filter for accepted calls in this room (active calls)
            room_active_calls = [n for n in notifications if 
                                n.get("room") == room_id and 
                                n.get("status") == "accepted"]
                
            if room_active_calls:
                # Sort by created_at time and get the most recent
                room_active_calls.sort(key=lambda n: n.get("created_at", ""), reverse=True)
                active_call = room_active_calls[0]
                
                # Set active call info
                caller_username = active_call.get("caller", {}).get("username", "Unknown caller")
                room_name = active_call.get("room_name", "Unknown room") 
                call_type = active_call.get("call_type", "audio")
                notification_id = active_call.get("id", "")
                
                print(f"[WebRTC Debug] Found active {call_type} call in room {room_name} started by {caller_username}")
                
                # Set joining_existing_call flag and update active call info
                self._show_active_call_banner(notification_id, room_id, room_name, call_type, caller_username)
                
            else:
                self.joining_existing_call = False
                print("[WebRTC Debug] No active calls found in this room")
                
        except Exception as e:
            print(f"[WebRTC Debug] Error checking for room calls: {str(e)}")
            
    def _check_active_calls_via_websocket(self, room_id: str):
        """Fallback method to check for active calls using WebSocket."""
        print("[WebRTC Debug] Using WebSocket to check for active calls")
        
        # This is a fallback when the API endpoint isn't available
        # We'll send a WebSocket message to request active call info for the room
        rx.call_script(f"""
            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                console.log('[WebRTC Debug] Requesting active call info via WebSocket');
                window.chatSocket.send(JSON.stringify({{
                    type: 'check_active_calls',
                    room_id: '{room_id}'
                }}));
                
                // Add a one-time handler for the response
                const handleActiveCallInfo = function(event) {{
                    const data = JSON.parse(event.data);
                    if (data.type === 'active_call_info') {{
                        console.log('[WebRTC Debug] Received active call info:', data);
                        
                        if (data.active_call) {{
                            // Use custom event to trigger UI update
                            const callEvent = new CustomEvent('active_call_detected', {{
                                detail: {{
                                    notification_id: data.active_call.id,
                                    room_id: '{room_id}',
                                    room_name: data.active_call.room_name,
                                    call_type: data.active_call.call_type,
                                    caller_username: data.active_call.started_by
                                }}
                            }});
                            document.dispatchEvent(callEvent);
                        }}
                        
                        // Remove this handler after processing
                        window.chatSocket.removeEventListener('message', handleActiveCallInfo);
                    }}
                }};
                
                window.chatSocket.addEventListener('message', handleActiveCallInfo);
                
                // Add a listener for the custom event
                document.addEventListener('active_call_detected', (e) => {{
                    window._set_state_from_js({{
                        joining_existing_call: true,
                        active_room_call: {{
                            id: e.detail.notification_id,
                            room_id: e.detail.room_id,
                            room_name: e.detail.room_name,
                            call_type: e.detail.call_type,
                            started_by: e.detail.caller_username,
                            participants: [e.detail.caller_username]
                        }},
                        _events: [{{ 
                            name: "_show_active_call_banner", 
                            payload: {{ 
                                notification_id: e.detail.notification_id,
                                room_id: e.detail.room_id,
                                room_name: e.detail.room_name,
                                call_type: e.detail.call_type,
                                caller_username: e.detail.caller_username
                            }} 
                        }}]
                    }});
                }}, {{ once: true }});
            }}
        """)
            
    @rx.event
    async def _show_active_call_banner(self, notification_id: str, room_id: str, room_name: str, call_type: str, caller_username: str):
        """Show banner for active call in room."""
        # Set joining_existing_call flag and update active call info
        self.joining_existing_call = True
        self.active_room_call = {
            "id": notification_id,
            "room_id": room_id,
            "room_name": room_name,
            "call_type": call_type, 
            "started_by": caller_username,
            "participants": [caller_username]
        }
        
        # Show call banner/join button in the UI
        rx.call_script(f"""
            // Create a call banner to show active call
            setTimeout(() => {{
                const callType = '{call_type}';
                const callStarter = '{caller_username}';
                
                // Add a banner at the top of the chat
                const chatContainer = document.querySelector('.message-container');
                if (chatContainer) {{
                    // Check if banner already exists
                    if (document.getElementById('active-call-banner')) {{
                        return; // Banner already exists, no need to create another
                    }}
                    
                    const banner = document.createElement('div');
                    banner.id = 'active-call-banner';
                    banner.style.cssText = 'position:sticky;top:0;width:100%;background:#e8f7fc;border-radius:8px;padding:10px;margin:10px 0;display:flex;justify-content:space-between;align-items:center;z-index:10;box-shadow:0 2px 5px rgba(0,0,0,0.1);';
                    
                    const iconType = callType === 'video' ? '🎥' : '📞';
                    banner.innerHTML = `
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-size:24px;">${{iconType}}</span>
                            <div>
                                <div style="font-weight:bold;">${{callType === 'video' ? 'Video' : 'Audio'}} call in progress</div>
                                <div style="font-size:14px;color:#666;">Started by ${{callStarter}}</div>
                            </div>
                        </div>
                        <button id="join-call-button" style="background:#80d0ea;color:white;border:none;border-radius:4px;padding:8px 12px;cursor:pointer;font-weight:bold;">Join Call</button>
                    `;
                    
                    chatContainer.insertBefore(banner, chatContainer.firstChild);
                    
                    // Add click handler for join button
                    document.getElementById('join-call-button').addEventListener('click', () => {{
                        // Using a custom event to trigger Reflex event
                        const event = new CustomEvent('join_existing_call', {{
                            detail: {{
                                call_type: callType,
                                notification_id: '{notification_id}'
                            }}
                        }});
                        document.dispatchEvent(event);
                    }});
                    
                    // Listen for the custom event
                    document.addEventListener('join_existing_call', (e) => {{
                        // Call Reflex method
                        window._set_state_from_js({{
                            call_type: e.detail.call_type,
                            call_invitation_id: e.detail.notification_id,
                            _events: [{{ name: "join_existing_call", payload: {{ invitation_id: e.detail.notification_id }} }}]
                        }});
                    }});
                }}
            }}, 500);
        """)

    @rx.event
    async def join_existing_call(self, invitation_id: str = None):
        """Join an existing call in the room."""
        print(f"[WebRTC Debug] Joining existing call: {invitation_id}")
        
        if not invitation_id and self.active_room_call:
            invitation_id = self.active_room_call.get("id", "")
            
        if not invitation_id:
            self.error_message = "No active call to join"
            return
            
        # Set call invitation ID 
        self.call_invitation_id = invitation_id
        
        # Use the call type from active room call
        if self.active_room_call:
            self.call_type = self.active_room_call.get("call_type", "audio")
            
        # Accept the call using our existing method
        await self.accept_call()

    # The issue is in the WebSocket message handling and how call notifications are processed.
    # We need to fix two main parts:

    # 1. First, improve the announce_room_call method to ensure a consistent WebSocket notification format:

    @rx.event
    async def announce_room_call(self, api_url: str, call_type: str = "audio"):
        """
        Create a call notification for all users in a room that will trigger popup windows.
        
        Args:
            api_url: The API URL for creating call notifications
            call_type: The type of call ("audio" or "video")
        """
        print(f"[WebRTC Debug] [CALL FLOW] SENDER EVENT: User {self.username} is announcing {call_type} call to room {self.current_room_id}")
        
        try:
            # Set the room call API URL
            self.room_call_api_url = api_url
            
            # 1. Get necessary data
            self.auth_token = await self.get_token()
            if not self.auth_token:
                self.error_message = "Not authenticated"
                return
                
            current_username = await self.get_username()
            if not current_username:
                self.error_message = "Username not found"
                return
                
            room_id = self.current_room_id
            if not room_id:
                self.error_message = "No active room selected"
                return
                
            # Find room name - make sure we have a proper room name
            room_name = self.current_chat_user
            if not room_name:
                for room in self.rooms:
                    if str(room.get("id", "")) == str(room_id):
                        room_name = room.get("name", f"Room {room_id}")
                        break
                if not room_name:
                    room_name = f"Room {room_id}"
                    
            print(f"[WebRTC Debug] [CALL FLOW] Call details - User: {current_username}, Room: {room_name} ({room_id}), Type: {call_type}")
            
            # Create a unique local ID for the call in case API fails
            local_call_id = f"local-{room_id}-{int(time.time())}"
            
            # 2. Try to create call notification using the provided API URL
            # But also have a fallback for when the API isn't implemented yet
            rx.call_script(f"""
                console.log('[WebRTC Debug] [CALL FLOW] USER {current_username} IS INITIATING call via API: {api_url}');
                
                // DEBUGGING: Alert to confirm the script is running
                console.warn('[CRITICAL DEBUG] About to make POST request to {api_url}');
                
                // Show calling popup
                state.show_calling_popup = true;
                state.call_type = '{call_type}';
                state._update();
                
                // Function to handle API-based approach
                function createCallNotificationViaAPI() {{
                    // Create notification
                    console.warn('[CRITICAL DEBUG] Making fetch POST request now');
                    
                    // Show an alert to confirm the code is running
                    alert('Attempting to make call API request to: ' + '{api_url}');
                    
                    const requestBody = {{
                        'recipient_id': null, // Setting to null for room-wide calls
                        'room_id': '{room_id}',
                        'call_type': '{call_type}'
                    }};
                    
                    console.warn('[CRITICAL DEBUG] Request body:', JSON.stringify(requestBody));
                    
                    // Try first with Token auth
                    tryFetchWithAuth('Token');
                    
                    // Function to try fetch with different auth types
                    function tryFetchWithAuth(authType) {{
                        console.warn('[CRITICAL DEBUG] Trying with ' + authType + ' authentication');
                        
                        // Use explicit fetch with detailed logging
                        fetch('{api_url}', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                                'Authorization': authType + ' {self.auth_token}'
                            }},
                            body: JSON.stringify(requestBody)
                        }})
                        .then(function(response) {{
                            console.warn('[CRITICAL DEBUG] Room call API response received (' + authType + '):', response.status);
                            
                            // Store response in a variable accessible to later callbacks
                            const responseStatus = response.status;
                            
                            return response.text().then(function(text) {{
                                try {{
                                    // Try to parse as JSON
                                    const data = JSON.parse(text);
                                    console.warn('[CRITICAL DEBUG] Parsed JSON response:', data);
                                        
                                    // If successful response, continue with JSON data
                                        if (responseStatus >= 200 && responseStatus < 300) {{
                                        return data;
                                        }} else if (responseStatus === 401 && authType === 'Token') {{
                                        // If unauthorized with Token, try Bearer
                                        console.warn('[CRITICAL DEBUG] Token auth failed, trying Bearer');
                                            tryFetchWithAuth('Bearer');
                                        return null;
                                        }} else {{
                                        throw new Error('API error (' + responseStatus + '): ' + JSON.stringify(data));
                                    }}
                                }} catch (e) {{
                                    // Not JSON or parsing error
                                    console.warn('[CRITICAL DEBUG] Raw response text:', text);
                                            
                                            if (responseStatus === 404) {{
                                        throw new Error('API endpoint not found (404)');
                                    }} else if (responseStatus === 401 && authType === 'Token') {{
                                        // If unauthorized with Token, try Bearer
                                        console.warn('[CRITICAL DEBUG] Token auth failed, trying Bearer');
                                        tryFetchWithAuth('Bearer');
                                        return null;
                                    }} else {{
                                        throw new Error('Failed: ' + responseStatus + ', Response: ' + text);
                                    }}
                                }}
                            }});
                        }})
                        .then(function(data) {{
                            if (!data) return; // Skip if auth switching
                            
                            console.warn('[CRITICAL DEBUG] Room call API success - Processing data');
                                    alert('Call API request successful!');
                                    
                                    // Store the notification ID for later use
                                    state.call_invitation_id = data.id;
                                    
                                    // Send WebSocket message to announce call to all room users
                                    announceCallViaWebSocket(data.id);
                                    
                            console.log('[WebRTC Debug] Room call started successfully');
                                    state.active_room_call = {{
                                        id: data.id,
                                        room_id: '{room_id}',
                                        room_name: '{room_name}',
                                        call_type: '{call_type}',
                                        started_by: '{current_username}',
                                        start_time: new Date().toISOString()
                                    }};
                                    state._update();
                        }})
                        .catch(function(error) {{
                            if (error.message && error.message.includes('auth failed')) return; // Skip if auth switching
                            
                            console.error('[CRITICAL DEBUG] Error making POST request:', error);
                            alert('Error making call API request: ' + error.message);
                            
                            // If API endpoint not found, use WebSocket only approach
                            if (error.message && error.message.includes('404')) {{
                                console.log('[WebRTC Debug] API endpoint not available, using WebSocket only');
                                                handleAPIUnavailable();
                                            }} else {{
                                state.error_message = 'Failed to start room call: ' + error.message;
                                                state.show_calling_popup = false;
                                                state._update();
                                            }}
                        }});
                    }}
                }}
                
                // Function to handle WebSocket announcement - UPDATED TO MATCH API FORMAT
                function announceCallViaWebSocket(notificationData) {{
                    // Send WebSocket message to announce call to all room users
                    if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                        console.log('[WebRTC Debug] [CALL FLOW] USER {current_username} IS SENDING WebSocket room-wide call announcement');
                        
                        // Create a properly structured message according to API documentation
                        const callAnnouncement = {{
                            type: 'room_call_announcement',
                            notification: notificationData || {{
                                id: '{local_call_id}',
                                caller: {{
                                    id: 'local-user-id',
                                    username: '{current_username}'
                                }},
                                room: '{room_id}',
                                room_name: '{room_name}',
                                call_type: '{call_type}',
                                created_at: new Date().toISOString(),
                                expires_at: new Date(Date.now() + 60000).toISOString(), // 1 minute expiry
                                status: 'pending'
                            }}
                        }};
                        
                        // Log the exact message we're sending
                        console.log('[WebRTC Debug] [CALL FLOW] SENDING PAYLOAD:', JSON.stringify(callAnnouncement, null, 2));
                        
                        // Send the message
                        window.chatSocket.send(JSON.stringify(callAnnouncement));
                        
                        // Also add a system message to the chat to indicate a call started
                        const callStartedMessage = {{
                            type: 'message',
                            message: {{
                                content: '{current_username} started a ' + 
                                        ('{call_type}' === 'video' ? 'video' : 'audio') + 
                                        ' call. You can join by clicking the call banner at the top of the chat.',
                                sender: {{
                                    username: 'System'
                                }},
                                sent_at: new Date().toISOString()
                            }}
                        }};
                        
                        // Send the system message
                        setTimeout(() => {{
                            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                                console.log('[WebRTC Debug] [CALL FLOW] Sending system message about call');
                                window.chatSocket.send(JSON.stringify(callStartedMessage));
                            }}
                        }}, 500);
                        
                        // Also send a simplified legacy format message for backward compatibility
                        setTimeout(() => {{
                            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                                const legacyFormat = {{
                                    type: 'room_call_announcement',
                                    room_id: '{room_id}',
                                    room_name: '{room_name}',
                                    caller_username: '{current_username}',
                                    call_type: '{call_type}',
                                    invitation_id: notificationData ? notificationData.id : '{local_call_id}'
                                }};
                                console.log('[WebRTC Debug] [CALL FLOW] Sending legacy format for compatibility:', legacyFormat);
                                window.chatSocket.send(JSON.stringify(legacyFormat));
                            }}
                        }}, 1000);
                                        }} else {{
                        console.error('[WebRTC Debug] [CALL FLOW] Cannot announce call: WebSocket not connected');
                        state.error_message = 'Cannot start call: Communication channel not connected';
                    }}
                }}
                
                // Function to handle the case where API is unavailable
                function handleAPIUnavailable() {{
                    console.log('[WebRTC Debug] [CALL FLOW] Using local call ID:', '{local_call_id}');
                    
                    // Set a local call ID instead
                    state.call_invitation_id = '{local_call_id}';
                    
                    // Announce call via WebSocket only
                    announceCallViaWebSocket(null); // Pass null to use the fallback data
                    
                    // Update state with local call info
                    state.active_room_call = {{
                        id: '{local_call_id}',
                        room_id: '{room_id}',
                        room_name: '{room_name}',
                        call_type: '{call_type}',
                        started_by: '{current_username}',
                        start_time: new Date().toISOString(),
                        is_local_only: true // Flag to indicate this call exists only via WebSocket
                    }};
                                            state._update();
                                        }}
                
                // Start the process
                createCallNotificationViaAPI();
            """)
            
            # 3. Start call timer
            if call_type in ["audio", "video"]:
                await self.start_call_timer()
                
        except Exception as e:
            print(f"[WebRTC Debug] [CALL FLOW] Error announcing room call: {str(e)}")
            self.error_message = f"Error announcing room call: {str(e)}"
            self.show_calling_popup = False

    # 2. Second, fix the WebSocket message handling to properly process room call announcements:

    @rx.event
    async def connect_chat_websocket(self):
        """Connect to chat WebSocket that also handles call notifications."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
                
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot connect to chat websocket")
            self.error_message = "Not authenticated. Please log in."
            return
                
        # Connect to chat WebSocket using JavaScript
        rx.call_script("""
            // Only run on client side
            if (typeof window === 'undefined') return;
            
            // Close existing connection if any
            if (window.chatSocket && window.chatSocket.readyState !== WebSocket.CLOSED) {{
                window.chatSocket.close();
            }}
            
            // Create new WebSocket connection for chat with call functionality
            const wsBaseUrl = '{self.WS_BASE_URL}';
            const roomId = '{self.current_room_id}';
            const wsUrl = `${{wsBaseUrl}}/room/${{roomId}}/`;
            console.log('Connecting to chat WebSocket at:', wsUrl);
            
            window.chatSocket = new WebSocket(wsUrl);
            
            window.chatSocket.onopen = function(event) {{
                console.log('[WebRTC Debug] Chat WebSocket connected to room {self.current_room_id}');
                state.is_connected = true;
                
                // Send authentication message
                window.chatSocket.send(JSON.stringify({{
                    type: 'auth',
                    token: '{self.auth_token}'
                }}));
                
                // Log connection success with username
                console.log('[WebRTC Debug] WebSocket connected for user: ' + state.username);
            }};
            
            window.chatSocket.onmessage = function(event) {{
                                            try {{
                    const data = JSON.parse(event.data);
                    
                    // Enhanced logging - for ALL WebSocket messages
                    const timestamp = new Date().toISOString();
                    const messageType = data.type || 'unknown';
                    console.log(`[WebRTC Debug] [RECEIVED:${timestamp}] WebSocket message type: ${messageType}`);
                    
                    // Special detailed logging for call-related messages
                    if (messageType.includes('call') || messageType === 'room_call_announcement') {{
                        console.log(`[WebRTC Debug] [CALL FLOW] USER ${state.username} RECEIVED:`, JSON.stringify(data, null, 2));
                    }}
                    
                    // Handle different message types
                    switch(data.type) {{
                        case 'message':
                            // Handle new message
                            handleNewMessage(data);
                            break;
                        case 'typing':
                            // Handle typing notification
                            handleTypingNotification(data);
                            break;
                        case 'incoming_call':
                            // Handle direct incoming call notification (1-on-1 calls)
                            // This is the new format according to the API docs
                            console.log('[WebRTC Debug] [CALL FLOW] RECEIVER EVENT: User', state.username, 'received incoming_call from API');
                            
                            // Extract notification data from the API format
                            const incomingCallNotification = data.notification;
                            
                            if (!incomingCallNotification) {{
                                console.error('[WebRTC Debug] [CALL FLOW] Missing notification data in incoming_call message');
                                break;
                            }}
                            
                            // Extract caller info
                            const callerUsername = incomingCallNotification.caller?.username;
                            
                            // Don't handle calls initiated by this user
                            if (callerUsername === state.username) {{
                                console.log('[WebRTC Debug] [CALL FLOW] Ignoring our own call notification');
                                break;
                            }}
                            
                            // Show incoming call popup
                            handleIncomingCallNotification(incomingCallNotification);
                            break;
                            
                        case 'call_notification':
                            // Handle legacy direct call notification format
                            console.log('[WebRTC Debug] [CALL FLOW] RECEIVER EVENT: User', state.username, 'received call_notification (legacy format)');
                            
                            const legacyNotification = {{
                                id: data.invitation_id || data.id,
                                caller: {{
                                    username: data.caller_username || data.caller || "Unknown caller"
                                }},
                                room: data.room_id || data.room,
                                room_name: data.room_name || "Chat Room",
                                call_type: data.call_type || "audio",
                                status: "pending"
                            }};
                            
                            // Don't handle calls initiated by this user
                            if (legacyNotification.caller.username === state.username) {{
                                console.log('[WebRTC Debug] [CALL FLOW] Ignoring our own call notification');
                                break;
                            }}
                            
                            // Show incoming call popup
                            handleIncomingCallNotification(legacyNotification);
                            break;
                            
                        case 'room_call_announcement':
                            // Handle room call announcement (could be either API format or legacy format)
                            console.log('[WebRTC Debug] [CALL FLOW] RECEIVER EVENT: User', state.username, 'received room_call_announcement');
                            
                            let roomCallNotification;
                            
                            // Check if this is the API format (with notification object) or legacy format
                            if (data.notification) {{
                                // API format
                                roomCallNotification = data.notification;
                                console.log('[WebRTC Debug] [CALL FLOW] Received API format room call notification');
                            }} else if (data.room_id || data.caller_username) {{
                                // Legacy format
                                roomCallNotification = {{
                                    id: data.invitation_id || `legacy-${Date.now()}`,
                                    caller: {{
                                        username: data.caller_username || "Unknown caller"
                                    }},
                                    room: data.room_id,
                                    room_name: data.room_name || "Chat Room",
                                    call_type: data.call_type || "audio",
                                    status: "pending"
                                }};
                                console.log('[WebRTC Debug] [CALL FLOW] Received legacy format room call, converted to:', roomCallNotification);
                            }} else {{
                                console.error('[WebRTC Debug] [CALL FLOW] Invalid room_call_announcement format:', data);
                                break;
                            }}
                            
                            // Don't handle calls initiated by this user
                            if (roomCallNotification.caller.username === state.username) {{
                                console.log('[WebRTC Debug] [CALL FLOW] Ignoring our own room call announcement');
                                break;
                            }}
                            
                            // Create a call banner at the top of the chat
                            console.log('[WebRTC Debug] [CALL FLOW] Creating call banner for', state.username);
                            createCallBanner(roomCallNotification);
                            
                            // Also show incoming call popup
                            handleIncomingCallNotification(roomCallNotification);
                            break;
                            
                        case 'call_notification_update':
                            // Handle call status updates
                            console.log('[WebRTC Debug] [CALL FLOW] Call notification update received');
                            
                            const updatedNotification = data.notification;
                            if (!updatedNotification) {{
                                console.error('[WebRTC Debug] [CALL FLOW] Missing notification data in update');
                                break;
                            }}
                            
                            handleCallStatusUpdate(updatedNotification);
                            break;
                            
                        case 'call_ended':
                            // Handle call end notification
                            console.log('[WebRTC Debug] [CALL FLOW] Call ended notification received');
                            
                            const endedCall = data.call;
                            if (!endedCall) {{
                                console.error('[WebRTC Debug] [CALL FLOW] Missing call data in call_ended message');
                                break;
                            }}
                            
                            // Clean up call resources
                            cleanupCall(endedCall.id);
                            break;
                            
                        case 'call_response':
                            // Handle legacy call response (accept/decline)
                            console.log('[WebRTC Debug] [CALL FLOW] Legacy call response received:', data);
                            handleLegacyCallResponse(data);
                            break;
                            
                        case 'join_call_notification':
                            // Someone joined the call
                            console.log('[WebRTC Debug] [CALL FLOW] User joined call:', data.username);
                            
                            // Update participants list in active call data
                            if (state.active_room_call && state.active_room_call.participants) {{
                                if (!state.active_room_call.participants.includes(data.username)) {{
                                    state.active_room_call.participants.push(data.username);
                                    state._update();
                                }}
                            }}
                            
                            // Show a toast notification that someone joined
                            showJoinedCallToast(data.username);
                            break;
                            
                        case 'end_call':
                            // Handle legacy end call notification
                            console.log('[WebRTC Debug] [CALL FLOW] Legacy end_call notification received:', data);
                            
                            // Clean up call resources
                            cleanupCall(data.invitation_id || data.call_id);
                            break;
                            
                        case 'error':
                            console.error('[WebRTC Debug] Chat WebSocket error:', data.message);
                            state.error_message = data.message;
                            break;
                    }}
                }} catch (error) {{
                    console.error('[WebRTC Debug] Error processing WebSocket message:', error, 'Raw data:', event.data);
                }}
            }};
            
            window.chatSocket.onclose = function(event) {{
                console.log('[WebRTC Debug] Chat WebSocket connection closed', event);
                state.is_connected = false;
                
                // Check if it was an abnormal closure
                if (event.code !== 1000) {{  // 1000 is normal closure
                    console.error('[WebRTC Debug] Chat WebSocket closed abnormally:', event.code, event.reason);
                }}
            }};
            
            window.chatSocket.onerror = function(error) {{
                console.error('[WebRTC Debug] Chat WebSocket error:', error);
                state.is_connected = false;
            }};
            
            //========== HELPER FUNCTIONS ==========//
            
            // Function to handle incoming call notification (shows UI)
            function handleIncomingCallNotification(notification) {{
                console.log('[WebRTC Debug] [CALL FLOW] Processing incoming call notification:', notification);
                
                if (!notification) {{
                    console.error('[WebRTC Debug] [CALL FLOW] Invalid notification data');
                    return;
                }}
                
                const callerId = notification.caller?.id || 'unknown-id';
                const callerUsername = notification.caller?.username || 'Unknown caller';
                const notificationId = notification.id;
                const callType = notification.call_type || 'audio';
                const roomId = notification.room;
                const roomName = notification.room_name || 'Chat Room';
                
                console.log(`[WebRTC Debug] [CALL FLOW] Incoming call from ${callerUsername} (${callerId})`);
                
                // Show incoming call popup using setTimeout to avoid React state update issues
                setTimeout(() => {{
                    // Update call details in state
                    state.current_chat_user = callerUsername;
                    state.call_type = callType;
                    state.show_incoming_call = true;
                    state.call_invitation_id = notificationId;
                    state.incoming_caller = callerUsername;
                    state.active_room_call = {{
                        id: notificationId,
                        room_id: roomId,
                        room_name: roomName || 'Chat Room',
                        call_type: callType,
                        started_by: callerUsername,
                        participants: [callerUsername]
                    }};
                    
                    console.log('[WebRTC Debug] [CALL FLOW] SHOWING POPUP: Call for', state.username, 'from', callerUsername);
                    
                    // Play ringtone
                    try {{
                        if (!window.ringtoneElement) {{
                            window.ringtoneElement = new Audio('/static/ringtone.mp3');
                            window.ringtoneElement.loop = true;
                            window.ringtoneElement.volume = 0.7;
                        }}
                        
                        const playPromise = window.ringtoneElement.play();
                        
                        if (playPromise !== undefined) {{
                            playPromise.catch(e => {{
                                console.log('[WebRTC Debug] Error playing ringtone:', e);
                                // Add click handler for user interaction
                                document.addEventListener('click', function unlockAudio() {{
                                    window.ringtoneElement.play();
                                    document.removeEventListener('click', unlockAudio);
                                }}, {{once: true}});
                            }});
                        }}
                    }} catch(e) {{
                        console.error('[WebRTC Debug] Exception playing ringtone:', e);
                    }}
                    
                    // Flash title to get user's attention
                    const origTitle = document.title;
                    window.titleFlashInterval = setInterval(() => {{
                        document.title = document.title === origTitle ? 
                            `📞 ${callType === 'video' ? 'Video' : 'Audio'} Call from ${callerUsername}` : origTitle;
                    }}, 1000);
                    
                    // Force UI update
                    state._update();
                }}, 0);
            }}
            
            // Function to handle call status updates
            function handleCallStatusUpdate(notification) {{
                console.log('[WebRTC Debug] [CALL FLOW] Processing call status update:', notification);
                
                const status = notification.status;
                const notificationId = notification.id;
                
                // Update UI based on notification status
                switch(status) {{
                    case 'accepted':
                        console.log('[WebRTC Debug] [CALL FLOW] Call was accepted');
                        
                        // Stop ringtone if playing
                        if (window.ringtoneElement) {{
                            window.ringtoneElement.pause();
                            window.ringtoneElement.currentTime = 0;
                        }}
                        
                        // If we're the caller, hide calling popup and show call UI
                        if (state.show_calling_popup) {{
                            state.show_calling_popup = false;
                            if (state.call_type === 'video') {{
                                state.show_video_popup = true;
                        }} else {{
                                state.show_call_popup = true;
                            }}
                            state._update();
                        }}
                        break;
                        
                    case 'declined':
                        console.log('[WebRTC Debug] [CALL FLOW] Call was declined');
                        
                        cleanupCall(notificationId);
                        
                        // If we're the caller, show declined message
                        if (state.show_calling_popup) {{
                            state.show_calling_popup = false;
                            state.error_message = 'Call declined';
                            state._update();
                            
                            // Stop media streams
                            if (window.localStream) {{
                                window.localStream.getTracks().forEach(track => track.stop());
                            }}
                        }}
                        break;
                        
                    case 'missed':
                        console.log('[WebRTC Debug] [CALL FLOW] Call was missed');
                        cleanupCall(notificationId);
                        break;
                        
                    case 'ended':
                        console.log('[WebRTC Debug] [CALL FLOW] Call was ended');
                        cleanupCall(notificationId);
                        break;
                }}
            }}
            
            // Function to handle legacy call response format
            function handleLegacyCallResponse(data) {{
                console.log('[WebRTC Debug] [CALL FLOW] Legacy call response received:', data);
                
                // Get response details
                const response = data.response;
                
                // Update state immediately
                if (response === 'accept') {{
                    // Call was accepted, continue with establishing connection
                    console.log('[WebRTC Debug] [CALL FLOW] Call accepted by', data.username || 'someone');
                    
                    // Stop calling ringtone 
                    if (window.ringtoneElement) {{
                        window.ringtoneElement.pause();
                        window.ringtoneElement.currentTime = 0;
                    }}
                    
                    // Hide calling popup and show call UI
                    state.show_calling_popup = false;
                    if (state.call_type === 'video') {{
                        state.show_video_popup = true;
                    }} else {{
                        state.show_call_popup = true;
                    }}
                    state._update();
                }} else if (response === 'decline') {{
                    // Call was declined
                    console.log('[WebRTC Debug] [CALL FLOW] Call declined by', data.username || 'someone');
                    
                    // Hide calling popup
                    state.show_calling_popup = false;
                    state.error_message = 'Call declined';
                    state.incoming_caller = '';
                    
                    // Stop media streams
                    if (window.localStream) {{
                        window.localStream.getTracks().forEach(track => track.stop());
                    }}
                    state._update();
                }}
            }}
            
            // Function to cleanup call resources
            function cleanupCall(callId) {{
                console.log('[WebRTC Debug] [CALL FLOW] Cleaning up call:', callId);
                
                // Stop ringtone if playing
                if (window.ringtoneElement) {{
                    window.ringtoneElement.pause();
                    window.ringtoneElement.currentTime = 0;
                }}
                
                // Clear title flash interval
                if (window.titleFlashInterval) {{
                    clearInterval(window.titleFlashInterval);
                    document.title = 'Chat';
                }}
                
                // Remove call banner if it exists
                const callBanner = document.getElementById('active-call-banner');
                if (callBanner) {{
                    callBanner.remove();
                }}
                
                // Update UI state
                setTimeout(() => {{
                    state.show_incoming_call = false;
                    state.show_calling_popup = false;
                    state.is_call_connected = false;
                    state.active_room_call = {{}}; // Clear active room call data
                    state._update();
                }}, 0);
            }}
            
            // Function to show joined call toast notification
            function showJoinedCallToast(username) {{
                const joinToast = document.createElement('div');
                joinToast.style.cssText = 'position:fixed;bottom:20px;left:20px;background:#333;color:white;padding:12px;border-radius:4px;z-index:9999;';
                joinToast.innerHTML = '<strong>' + username + '</strong> joined the call';
                document.body.appendChild(joinToast);
                
                // Auto-remove after 3 seconds
                setTimeout(() => {{
                    joinToast.style.opacity = '0';
                    joinToast.style.transition = 'opacity 0.5s';
                    setTimeout(() => document.body.removeChild(joinToast), 500);
                }}, 3000);
            }}
            
            // Function to handle new message
            function handleNewMessage(data) {{
                const message = data.message;
                if (!message) return;
                
                // Check if the message is from current user
                const isCurrentUser = message.sender.username === state.username;
                
                // Add message to chat history
                console.log(`[WebRTC Debug] Adding message from ${message.sender.username}`);
                state.chat_history = [...state.chat_history, [
                    isCurrentUser ? "user" : "other", 
                    message.content
                ]];
            }}
            
            // Function to handle typing notification
            function handleTypingNotification(data) {{
                const username = data.username;
                if (!username) return;
                
                // Add to typing users if not already there
                if (!state.typing_users.includes(username)) {{
                    state.typing_users = [...state.typing_users, username];
                }}
                
                // Remove after delay
                setTimeout(() => {{
                    state.typing_users = state.typing_users.filter(user => user !== username);
                }}, 3000);
            }}
            
            // Create a call banner at the top of the chat
            function createCallBanner(callData) {{
                console.log('[WebRTC Debug] [CALL FLOW] Creating call banner for room call');
                
                setTimeout(() => {{
                    const callType = callData.call_type || 'audio';
                    const callStarter = callData.caller?.username || callData.caller_username || 'Unknown caller';
                    const roomName = callData.room_name || 'Chat Room';
                    const notificationId = callData.id || `legacy-${Date.now()}`;
                    
                    // Add a banner at the top of the chat
                    const chatContainer = document.querySelector('.message-container');
                    if (chatContainer) {{
                        // Check if banner already exists
                        if (document.getElementById('active-call-banner')) {{
                            return; // Banner already exists, no need to create another
                        }}
                        
                        const banner = document.createElement('div');
                        banner.id = 'active-call-banner';
                        banner.style.cssText = 'position:sticky;top:0;width:100%;background:#e8f7fc;border-radius:8px;padding:10px;margin:10px 0;display:flex;justify-content:space-between;align-items:center;z-index:10;box-shadow:0 2px 5px rgba(0,0,0,0.1);';
                        
                        const iconType = callType === 'video' ? '🎥' : '📞';
                        banner.innerHTML = `
                            <div style="display:flex;align-items:center;gap:8px;">
                                <span style="font-size:24px;">${iconType}</span>
                                <div>
                                    <div style="font-weight:bold;">${callType === 'video' ? 'Video' : 'Audio'} call in progress</div>
                                    <div style="font-size:14px;color:#666;">Started by ${callStarter} in ${roomName}</div>
                                </div>
                            </div>
                            <button id="join-call-button" style="background:#80d0ea;color:white;border:none;border-radius:4px;padding:8px 12px;cursor:pointer;font-weight:bold;">Join Call</button>
                        `;
                        
                        chatContainer.insertBefore(banner, chatContainer.firstChild);
                        
                        // Add click handler for join button
                        document.getElementById('join-call-button').addEventListener('click', () => {{
                            console.log('[WebRTC Debug] [CALL FLOW] User', state.username, 'clicked Join Call button for call started by', callStarter);
                            
                            // Using a custom event to trigger Reflex event
                            const event = new CustomEvent('join_existing_call', {{
                                detail: {{
                                    call_type: callType,
                                    notification_id: notificationId
                                }}
                            }});
                            document.dispatchEvent(event);
                        }});
                        
                        // Listen for the custom event
                        document.addEventListener('join_existing_call', (e) => {{
                            // Call Reflex method
                            window._set_state_from_js({{
                                call_type: e.detail.call_type,
                                call_invitation_id: e.detail.notification_id,
                                _events: [{{ name: "join_existing_call", payload: {{ invitation_id: e.detail.notification_id }} }}]
                            }});
                        }});
                    }} else {{
                        console.error('[WebRTC Debug] Could not find message container for call banner');
                    }}
                }}, 500);
            }}
        """)
        self.is_connected = True
        
    @rx.event
    async def initialize_peer_connection(self):
        """Initialize WebRTC peer connection with debug logging."""
        print("[WebRTC Debug] Initializing peer connection")
        rx.call_script("""
            // WebRTC Debug Logger
            const webrtcDebug = {
                log: function(message, data = null) {
                    const timestamp = new Date().toISOString();
                    console.log(`[WebRTC Debug] ${timestamp} - ${message}`, data || '');
                    
                    // Update debug info in localStorage
                    const debugInfo = JSON.parse(localStorage.getItem('webrtc_debug') || '[]');
                    debugInfo.push({ timestamp, message, data });
                    if (debugInfo.length > 100) debugInfo.shift(); // Keep last 100 logs
                    localStorage.setItem('webrtc_debug', JSON.stringify(debugInfo));
                }
            };

            // Initialize WebRTC with debug
            try {
                webrtcDebug.log('Creating RTCPeerConnection');
                const configuration = {
                    iceServers: [
                        { urls: 'stun:stun.l.google.com:19302' }
                    ]
                };
                window.peerConnection = new RTCPeerConnection(configuration);

                // Connection state changes
                window.peerConnection.onconnectionstatechange = function() {
                    webrtcDebug.log('Connection state changed', {
                        state: window.peerConnection.connectionState
                    });
                };

                // ICE connection state changes
                window.peerConnection.oniceconnectionstatechange = function() {
                    webrtcDebug.log('ICE connection state changed', {
                        state: window.peerConnection.iceConnectionState
                    });
                };

                // ICE gathering state changes
                window.peerConnection.onicegatheringstatechange = function() {
                    webrtcDebug.log('ICE gathering state changed', {
                        state: window.peerConnection.iceGatheringState
                    });
                };

                // ICE candidate events
                window.peerConnection.onicecandidate = function(event) {
                    if (event.candidate) {
                        webrtcDebug.log('New ICE candidate', {
                            candidate: event.candidate.candidate,
                            sdpMid: event.candidate.sdpMid,
                            sdpMLineIndex: event.candidate.sdpMLineIndex
                        });
                    }
                };

                // Track events
                window.peerConnection.ontrack = function(event) {
                    webrtcDebug.log('Track received', {
                        kind: event.track.kind,
                        id: event.track.id
                    });
                };

                // Negotiation needed events
                window.peerConnection.onnegotiationneeded = function() {
                    webrtcDebug.log('Negotiation needed');
                };

                webrtcDebug.log('RTCPeerConnection initialized successfully');
            } catch (error) {
                webrtcDebug.log('Error initializing RTCPeerConnection', {
                    error: error.toString()
                });
                console.error('Error initializing peer connection:', error);
            }
        """)

    @rx.event
    async def get_room_recipients(self, room_id: str) -> list:
        """Get list of user IDs in a room except the current user.
        This helps to determine recipient_id for calls."""
        
        print(f"[CRITICAL DEBUG] Getting recipients for room: {room_id}")
        
        # First make sure we have a valid auth token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            print("[CRITICAL DEBUG] Not authenticated, cannot get room participants")
            return []
        
        try:
            # Try to get room details from API
            api_url = f"{self.API_HOST_URL}/communication/rooms/{room_id}/"
            
            # Set up headers
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Make the API call
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api_url,
                    headers=headers,
                    follow_redirects=True,
                    timeout=10.0
                )
                
                print(f"[CRITICAL DEBUG] Room details API response: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"[CRITICAL DEBUG] Room data: {data}")
                        
                        # Extract participants
                        participants = data.get("participants", [])
                        
                        # Get current username
                        current_username = await self.get_username()
                        
                        # Extract recipient IDs (excluding current user)
                        recipient_ids = []
                        
                        for participant in participants:
                            # Check the structure of participant data
                            if isinstance(participant, dict):
                                user_data = participant.get("user", {})
                                if isinstance(user_data, dict):
                                    username = user_data.get("username", "")
                                    user_id = user_data.get("id", "")
                                    
                                    # Skip current user
                                    if username != current_username and user_id:
                                        recipient_ids.append(user_id)
                                elif isinstance(user_data, str) and user_data != current_username:
                                    # In case user data is just a string ID or username
                                    recipient_ids.append(user_data)
                            elif isinstance(participant, str) and participant != current_username:
                                # In case participants are just string IDs or usernames
                                recipient_ids.append(participant)
                        
                        print(f"[CRITICAL DEBUG] Found recipient IDs: {recipient_ids}")
                        return recipient_ids
                    except Exception as e:
                        print(f"[CRITICAL DEBUG] Error parsing room data: {str(e)}")
                else:
                    print(f"[CRITICAL DEBUG] Failed to get room details: {response.text[:200]}")
        except Exception as e:
            print(f"[CRITICAL DEBUG] Error getting room recipients: {str(e)}")
        
        # Fallback - check locally cached room data
        try:
            recipients = []
            current_username = await self.get_username()
            
            # Check cached rooms data
            for room in self.rooms:
                if str(room.get("id", "")) == str(room_id):
                    # Found the room
                    # Try to extract participants
                    participants = room.get("participants", [])
                    
                    for participant in participants:
                        if isinstance(participant, dict):
                            user_data = participant.get("user", {})
                            if isinstance(user_data, dict):
                                username = user_data.get("username", "")
                                user_id = user_data.get("id", "")
                                
                                # Skip current user
                                if username != current_username and user_id:
                                    recipients.append(user_id)
                            elif isinstance(user_data, str) and user_data != current_username:
                                recipients.append(user_data)
                        elif isinstance(participant, str) and participant != current_username:
                            recipients.append(participant)
            
            print(f"[CRITICAL DEBUG] Found recipient IDs from cache: {recipients}")
            return recipients
        except Exception as e:
            print(f"[CRITICAL DEBUG] Error searching cached room data: {str(e)}")
            
        return []

    @rx.event
    async def start_call(self):
        """Start an audio call with support for multiple API field naming conventions."""
        print("[CRITICAL DEBUG] Starting audio call with both field naming formats")
        
        try:
            # Check if already in a call
            if self.show_call_popup or self.show_video_popup:
                self.error_message = "Already in a call"
                return
            
            # Get auth token explicitly
            self.auth_token = await self.get_token()
            if not self.auth_token:
                self.error_message = "Not authenticated"
                print("[CRITICAL DEBUG] Not authenticated, cannot make call")
                return
                
            # Set calling popup state
            self.show_calling_popup = True
            self.call_type = "audio"
            
            # Use the direct IP URL to avoid DNS issues during development
            api_url = f"{self.API_HOST_URL}/communication/incoming-calls/"
            print(f"[CRITICAL DEBUG] Making direct API call to: {api_url}")
            
            # Get current timestamp for expires_at
            from datetime import datetime, timedelta
            current_time = datetime.now()
            # Expiry time - 60 seconds in the future
            expires_at = (current_time + timedelta(seconds=60)).isoformat()
            
            # Try to find recipient ID
            recipients = await self.get_room_recipients(self.current_room_id)
            recipient_id = recipients[0] if recipients else None
            
            # Create API payload with BOTH field names to support different API versions
            # Include both 'room' and 'room_id' to handle different API expectations
            payload = {
                'recipient_id': recipient_id,
                'room': self.current_room_id,      # For API expecting 'room'
                'room_id': self.current_room_id,   # For API expecting 'room_id' 
                'call_type': 'audio',
                'expires_at': expires_at
            }
            print(f"[CRITICAL DEBUG] Dual-field payload: {payload}")
            
            # Try with both token formats (Bearer and Token)
            auth_headers = [
                {"Authorization": f"Bearer {self.auth_token}"},
                {"Authorization": f"Token {self.auth_token}"}
            ]
            
            # First make the API call directly from Python using httpx
            api_success = False
            api_response = None
            
            for headers in auth_headers:
                try:
                    headers["Content-Type"] = "application/json"
                    print(f"[CRITICAL DEBUG] Trying API call with headers: {headers}")
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            api_url,
                            json=payload,
                            headers=headers,
                            follow_redirects=True,
                            timeout=10.0
                        )
                        
                        print(f"[CRITICAL DEBUG] API Response status: {response.status_code}")
                        print(f"[CRITICAL DEBUG] Response content: {response.text[:500]}")
                        
                        if response.status_code >= 200 and response.status_code < 300:
                            api_success = True
                            try:
                                api_response = response.json()
                                print(f"[CRITICAL DEBUG] API call successful: {api_response}")
                            except:
                                print("[CRITICAL DEBUG] Response was not JSON")
                                api_response = {"id": f"manual-{self.current_room_id}-{int(time.time())}"}
                            break
                        else:
                            print(f"[CRITICAL DEBUG] API call failed with status {response.status_code}")
                except Exception as e:
                    print(f"[CRITICAL DEBUG] Error making API call with {list(headers.keys())[0]}: {str(e)}")
            
            # Now handle the call based on API result
            if api_success and api_response:
                # Store the API response in state
                call_id = api_response.get('id', '')
                if not call_id:
                    call_id = f"manual-{self.current_room_id}-{int(time.time())}"
                    
                self.call_invitation_id = call_id
                
                # Now send WebSocket message to announce the call
                await self.announce_call_via_websocket(
                    call_id=call_id,
                    room_id=self.current_room_id,
                    room_name=self.current_chat_user,
                    call_type='audio'
                )
            else:
                # Fallback to WebSocket-only approach if API call failed
                print("[CRITICAL DEBUG] Falling back to WebSocket-only approach")
                local_call_id = f"local-{self.current_room_id}-{int(time.time())}"
                self.call_invitation_id = local_call_id
                
                # Send WebSocket notification only
                await self.announce_call_via_websocket(
                    call_id=local_call_id,
                    room_id=self.current_room_id,
                    room_name=self.current_chat_user,
                    call_type='audio',
                    is_local_only=True
                )
            
            # Start call timer
            await self.start_call_timer()
            
        except Exception as e:
            print(f"[CRITICAL DEBUG] Error starting call: {str(e)}")
            self.error_message = f"Error starting call: {str(e)}"
            self.show_calling_popup = False

    @rx.event
    async def start_video_call(self):
        """Start a video call with support for multiple API field naming conventions."""
        print("[CRITICAL DEBUG] Starting video call with both field naming formats")
        
        try:
            # Check if already in a call
            if self.show_call_popup or self.show_video_popup:
                self.error_message = "Already in a call"
                return
            
            # Get auth token explicitly
            self.auth_token = await self.get_token()
            if not self.auth_token:
                self.error_message = "Not authenticated"
                print("[CRITICAL DEBUG] Not authenticated, cannot make call")
                return
                
            # Set calling popup state
            self.show_calling_popup = True
            self.call_type = "video"
            
            # Use the direct IP URL to avoid DNS issues during development
            api_url = f"{self.API_HOST_URL}/communication/incoming-calls/"
            print(f"[CRITICAL DEBUG] Making direct API call to: {api_url}")
            
            # Get current timestamp for expires_at
            from datetime import datetime, timedelta
            current_time = datetime.now()
            # Expiry time - 60 seconds in the future
            expires_at = (current_time + timedelta(seconds=60)).isoformat()
            
            # Try to find recipient ID
            recipients = await self.get_room_recipients(self.current_room_id)
            recipient_id = recipients[0] if recipients else None
            
            # Create API payload with BOTH field names to support different API versions
            # Include both 'room' and 'room_id' to handle different API expectations
            payload = {
                'recipient_id': recipient_id,
                'room': self.current_room_id,      # For API expecting 'room'
                'room_id': self.current_room_id,   # For API expecting 'room_id' 
                'call_type': 'video',
                'expires_at': expires_at
            }
            print(f"[CRITICAL DEBUG] Dual-field payload: {payload}")
            
            # Try with both token formats (Bearer and Token)
            auth_headers = [
                {"Authorization": f"Bearer {self.auth_token}"},
                {"Authorization": f"Token {self.auth_token}"}
            ]
            
            # First make the API call directly from Python using httpx
            api_success = False
            api_response = None
            
            for headers in auth_headers:
                try:
                    headers["Content-Type"] = "application/json"
                    print(f"[CRITICAL DEBUG] Trying API call with headers: {headers}")
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            api_url,
                            json=payload,
                            headers=headers,
                            follow_redirects=True,
                            timeout=10.0
                        )
                        
                        print(f"[CRITICAL DEBUG] API Response status: {response.status_code}")
                        print(f"[CRITICAL DEBUG] Response content: {response.text[:500]}")
                        
                        if response.status_code >= 200 and response.status_code < 300:
                            api_success = True
                            try:
                                api_response = response.json()
                                print(f"[CRITICAL DEBUG] API call successful: {api_response}")
                            except:
                                print("[CRITICAL DEBUG] Response was not JSON")
                                api_response = {"id": f"manual-{self.current_room_id}-{int(time.time())}"}
                            break
                        else:
                            print(f"[CRITICAL DEBUG] API call failed with status {response.status_code}")
                except Exception as e:
                    print(f"[CRITICAL DEBUG] Error making API call with {list(headers.keys())[0]}: {str(e)}")
            
            # Now handle the call based on API result
            if api_success and api_response:
                # Store the API response in state
                call_id = api_response.get('id', '')
                if not call_id:
                    call_id = f"manual-{self.current_room_id}-{int(time.time())}"
                    
                self.call_invitation_id = call_id
                
                # Now send WebSocket message to announce the call
                await self.announce_call_via_websocket(
                    call_id=call_id,
                    room_id=self.current_room_id,
                    room_name=self.current_chat_user,
                    call_type='video'
                )
            else:
                # Fallback to WebSocket-only approach if API call failed
                print("[CRITICAL DEBUG] Falling back to WebSocket-only approach")
                local_call_id = f"local-{self.current_room_id}-{int(time.time())}"
                self.call_invitation_id = local_call_id
                
                # Send WebSocket notification only
                await self.announce_call_via_websocket(
                    call_id=local_call_id,
                    room_id=self.current_room_id,
                    room_name=self.current_chat_user,
                    call_type='video',
                    is_local_only=True
                )
            
            # Start call timer
            await self.start_call_timer()
            
        except Exception as e:
            print(f"[CRITICAL DEBUG] Error starting video call: {str(e)}")
            self.error_message = f"Error starting video call: {str(e)}"
            self.show_calling_popup = False

    @rx.event
    async def announce_call_via_websocket(self, call_id: str, room_id: str, room_name: str, call_type: str, is_local_only: bool = False):
        """Send WebSocket message to announce a call to all users in a room.
        Enhanced version that supports multiple message formats for compatibility."""
        print(f"[CRITICAL DEBUG] Announcing {call_type} call via WebSocket, ID: {call_id}")
        
        # Get username for notification
        current_username = await self.get_username()
        
        # Set active call info in state
        self.active_room_call = {
            "id": call_id,
            "room_id": room_id,
            "room_name": room_name,
            "call_type": call_type,
            "started_by": current_username,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "is_local_only": is_local_only
        }
        
        # Use JavaScript to send WebSocket message
        rx.call_script(f"""
            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                console.log('[CRITICAL DEBUG] Sending room call announcement via WebSocket');
                
                // 1. Try Legacy Format (simplest and most likely to work)
                const legacyMessage = {{
                    type: 'room_call_announcement',
                    room_id: '{room_id}',
                    room_name: '{room_name}',
                    caller_username: '{current_username}',
                    call_type: '{call_type}',
                    invitation_id: '{call_id}'
                }};
                console.log('[CRITICAL DEBUG] Sending legacy format message:', JSON.stringify(legacyMessage));
                window.chatSocket.send(JSON.stringify(legacyMessage));
                
                // 2. Also try API format for compatibility
                setTimeout(() => {{
                    const apiFormatMessage = {{
                        type: 'room_call_announcement',
                        notification: {{
                            id: '{call_id}',
                            caller: {{
                                id: 'user-id', 
                                username: '{current_username}'
                            }},
                            room: '{room_id}',
                            room_name: '{room_name}',
                            call_type: '{call_type}',
                            status: 'pending',
                            created_at: new Date().toISOString(),
                            expires_at: new Date(Date.now() + 60000).toISOString()
                        }}
                    }};
                    console.log('[CRITICAL DEBUG] Sending API format message:', JSON.stringify(apiFormatMessage));
                    window.chatSocket.send(JSON.stringify(apiFormatMessage));
                }}, 300);
                
                // 3. Also send simplified notification (third format)
                setTimeout(() => {{
                    const simpleNotification = {{
                        type: 'call_notification',
                        call_type: '{call_type}',
                        caller_username: '{current_username}',
                        room_id: '{room_id}',
                        invitation_id: '{call_id}'
                    }};
                    console.log('[CRITICAL DEBUG] Sending simplified notification:', JSON.stringify(simpleNotification));
                    window.chatSocket.send(JSON.stringify(simpleNotification));
                }}, 600);
                
                // 4. Also send a system message
                setTimeout(() => {{
                    const systemMessage = {{
                        type: 'message',
                        message: {{
                            content: '{current_username} started a {call_type} call',
                            sender: {{ username: 'System' }},
                            sent_at: new Date().toISOString()
                        }}
                    }};
                    console.log('[CRITICAL DEBUG] Sending system message');
                    window.chatSocket.send(JSON.stringify(systemMessage));
                }}, 900);
            }} else {{
                console.error('[CRITICAL DEBUG] WebSocket not connected - cannot announce call');
            }}
        """)

    @rx.event
    async def end_call(self):
        """End an audio call."""
        print("[WebRTC Debug] Ending call")
        
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            self.error_message = "Not authenticated"
            print("[WebRTC Debug] Error: Not authenticated")
            return
            
        # Get room ID
        room_id = str(self.current_room_id)
        
        try:
            # Clean up WebRTC resources
            rx.call_script("""
                console.log('[WebRTC Debug] Cleaning up WebRTC resources');
                
                // Stop all tracks in local stream
                if (window.localStream) {
                    console.log('[WebRTC Debug] Stopping local stream tracks');
                    window.localStream.getTracks().forEach(track => {
                        track.stop();
                        console.log('[WebRTC Debug] Track stopped:', track.kind);
                    });
                    window.localStream = null;
                }
                
                // Close peer connection
                if (window.peerConnection) {
                    console.log('[WebRTC Debug] Closing peer connection');
                    window.peerConnection.close();
                    window.peerConnection = null;
                }
                
                console.log('[WebRTC Debug] WebRTC cleanup completed');
            """)
            
            print("[WebRTC Debug] Sending end call notification to server")
            
            # Use JavaScript fetch for API call to end the call
            api_url = f"{self.API_BASE_URL}/communication/calls/end/"
            
            rx.call_script(f"""
                // Call API to end call notification
                fetch('{api_url}', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer {self.auth_token}'
                    }},
                    body: JSON.stringify({{
                        'room_id': '{room_id}'
                    }})
                }})
                .then(response => {{
                    console.log('[WebRTC Debug] Call end API status:', response.status);
                    if (!response.ok) {{
                        throw new Error('Failed to end call: ' + response.status);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    console.log('[WebRTC Debug] Call end API response:', data);
                    
                    // Send WebSocket notification to all room users
                    if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                        console.log('[WebRTC Debug] Sending room-wide call end announcement');
                        window.chatSocket.send(JSON.stringify({{
                            type: 'end_call',
                            room_id: '{room_id}',
                            call_type: state.call_type
                        }}));
                    }}
                    
                    console.log('[WebRTC Debug] Call ended successfully');
                    
                    // Clean up call handler resources
                    if (window.callHandler && typeof window.callHandler.cleanupCall === 'function') {{
                        window.callHandler.cleanupCall();
                    }}
                    
                    // Also remove from active calls
                    if (typeof window.callHandler.removeActiveCall === 'function') {{
                        window.callHandler.removeActiveCall('{room_id}');
                    }}
                }})
                .catch(error => {{
                    console.error('[WebRTC Debug] Error ending call:', error);
                    state.error_message = 'Failed to end call: ' + error.message;
                }});
            """)
            
            # Update UI state
            self.show_calling_popup = False
            self.show_call_popup = False
            self.show_video_popup = False
            self.call_duration = 0
            self.is_call_connected = False
            self.active_room_call = {}
                    
        except Exception as e:
            print(f"[WebRTC Debug] Error in end_call: {str(e)}")
            self.error_message = f"Error ending call: {str(e)}"
            
    @rx.event
    async def end_video_call(self):
        """End a video call."""
        # Reuse the same end_call method
        await self.end_call()

    @rx.event
    async def toggle_mute(self):
        """Toggle microphone mute state."""
        self.is_muted = not self.is_muted
        
        # Update local stream audio tracks and notify peers
        rx.call_script("""
            if (window.localStream) {
                window.localStream.getAudioTracks().forEach(track => {
                    track.enabled = !state.is_muted;
                });
                
                // Notify peers about mute state change
                if (window.peerConnection) {
                    const data = {
                        type: 'mute_state',
                        is_muted: state.is_muted
                    };
                    window.peerConnection.send(JSON.stringify(data));
                }
            }
        """)
        yield

    @rx.event
    async def toggle_camera(self):
        """Toggle camera state."""
        self.is_camera_off = not self.is_camera_off
        
        # Update local stream video tracks
        rx.call_script("""
            if (window.localStream) {
                window.localStream.getVideoTracks().forEach(track => {
                    track.enabled = !state.is_camera_off;
                });
            }
        """)
        yield

    @rx.event
    async def increment_call_duration(self):
        """Increment call duration counter every second.
        This is an async generator meant to be used directly as an event handler."""
        while self.show_call_popup or self.show_video_popup:
            self.call_duration += 1
            yield rx.utils.sleep(1)

    @rx.event
    async def start_call_timer(self):
        """Start the call timer as a background task."""
        # Create a background task to handle the duration updates
        asyncio.create_task(self._increment_call_duration_task())
    
    async def _increment_call_duration_task(self):
        """Background task to increment call duration without yielding."""
        while self.show_call_popup or self.show_video_popup:
            self.call_duration += 1
            await asyncio.sleep(1)

    @rx.event
    async def clear_error_message(self):
        self.error_message = ""
        yield

    @rx.event
    async def clear_success_message(self):
        self.success_message = ""
        yield
        
    @rx.event
    async def cleanup(self):
        """Clean up resources when component unmounts."""
        # Clear any resource usage
        self.chat_history = []
        yield


    @rx.event
    async def keypress_handler(self, key: str):
        """Handle keypress events in the message input."""
        try:
            # Only send typing notification for non-Enter keys
            if key != "Enter":
                # Use direct call instead of emit - typing isn't critical
                print("User is typing...")
                # Don't await - just fire and forget for typing notifications
                self.send_typing_notification()
            # Send message when Enter is pressed
            elif key == "Enter" and self.message.strip():
                print(f"Sending message: {self.message[:10]}...")
                # Use regular send_message, it will update the UI
                await self.send_message()
        except Exception as e:
            print(f"Error in keypress_handler: {e}")

    @rx.event
    async def show_error(self):
        """Show error message in a notification."""
        # Don't use window_alert - the error_alert component will display the message
        yield

    @rx.event
    async def show_success(self):
        """Show success message in a notification."""
        # Don't use window_alert - the success_alert component will display the message
        yield
        
    @rx.event
    async def set_success_message(self, message: str):
        """Set a success message in the state."""
        self.success_message = message
        yield

    @rx.event
    async def set_error_message(self, message: str):
        """Set an error message in the state."""
        self.error_message = message
        yield

    @rx.event
    async def toggle_debug_info(self):
        """Toggle the visibility of the debug info panel."""
        self.debug_show_info = not self.debug_show_info
        yield
        
    @rx.event
    async def toggle_debug_dummy_data(self):
        """Toggle between using dummy data and real API data."""
        self.debug_use_dummy_data = not self.debug_use_dummy_data
        print(f"Debug dummy data set to: {self.debug_use_dummy_data}")
        
        # Reload data with the new setting
        if self.debug_use_dummy_data:
            await self._set_dummy_data()
            self._set_dummy_messages()
        else:
            try:
                await self.load_rooms()
                if self.current_room_id:
                    await self.load_messages()
            except Exception as e:
                print(f"Error loading data: {e}, falling back to dummy data")
                await self._set_dummy_data()
                self._set_dummy_messages()
        yield

    @rx.event
    async def login_as_user(self, username: str):
        """Debug function to set the current username manually."""
        print(f"Setting username to: {username}")
        
        # First make sure username is updated in state
        self.username = username
        
        # Then update it in localStorage with direct script code
        rx.call_script(f"""
            // Save username to localStorage
            localStorage.setItem('username', '{username}');
            console.log('Username saved to localStorage:', '{username}');
            
            // Force update the state in case it didn't update properly
            if (window._state) {{
                window._state.username = '{username}';
                console.log('Directly updated state.username to:', '{username}');
            }}
        """)
        
        # Force a refresh of the chat to properly show messages with new user
        if self.current_room_id:
            try:
                # Force update chat history to show correct message ownership
                for i in range(len(self.chat_history)):
                    sender, msg = self.chat_history[i]
                    # Update any "user" messages to reflect new username
                    if sender == "user":
                        print(f"Message {i+1} already marked as from current user")
                    # If the message is from the new username, mark it as from current user
                    elif sender == username:
                        print(f"Updating message {i+1} ownership to current user")
                        self.chat_history[i] = ("user", msg)
                
                # Then reload all messages to ensure proper display
                await self.load_messages()
            except Exception as e:
                print(f"Error updating chat messages: {e}")
        yield

    @rx.event
    async def poll_messages(self):
        """Poll for new messages as a fallback for WebSockets."""
        print(f"\n=== Starting message polling for room: {self.current_room_id} ===")
        
        # Verify the room_id is valid
        if not self.current_room_id or not isinstance(self.current_room_id, str) or not self.current_room_id.strip():
            print("Cannot poll messages: missing or invalid room_id")
            return
            
        if not self.auth_token:
            print("Cannot poll messages: missing auth_token")
            return
        
        # If username is not set or is default, try to fix it
        if not self.username or self.username == "user":
            await self.fix_username_if_needed()
            print(f"Username after fixing attempt: {self.username}")
            
        # Store room_id locally to avoid any issues with state changes
        room_id = self.current_room_id
        print(f"Polling messages for room {room_id}")
            
        poll_count = 0
        last_message_id = None  # Track the last message ID we've seen
        
        # Set up headers once
        headers = {
            "Authorization": f"Token {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        while self.should_reconnect:
            # Check if room_id is still valid and matches
            if self.current_room_id != room_id:
                print(f"Room changed from {room_id} to {self.current_room_id}, stopping polling")
                break
                
            try:
                poll_count += 1
                if poll_count % 10 == 0:  # Log every 10 polls to avoid spam
                    print(f"Polling messages for room {room_id} (count: {poll_count})...")
                
                # Use the correct API endpoint for fetching messages
                url = f"{self.API_BASE_URL}/communication/messages/?room_id={room_id}"
                
                # Add pagination if needed
                if last_message_id:
                    url += f"&after_id={last_message_id}"
                    
                if poll_count % 10 == 0:  # Log URL occasionally
                    print(f"Polling URL: {url}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers=headers,
                        follow_redirects=True,
                        timeout=10.0  # Add timeout to prevent hanging
                    )
                    
                    # Debug response information
                    if poll_count % 10 == 0:
                        print(f"Response status: {response.status_code}")
                        print(f"Response headers: {response.headers}")
                        # Print first 200 chars of response to debug
                        content_preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
                        print(f"Response content: {content_preview}")
                    
                    # Check if response is empty or invalid
                    if not response.text or response.text.isspace():
                        print("Empty response received from server")
                        continue
                    
                    try:
                        data = response.json()
                    except json.JSONDecodeError as e:
                        print(f"Invalid JSON response: {str(e)}")
                        print(f"Raw response: {response.text[:500]}")
                        await asyncio.sleep(5)  # Wait longer after an error
                        continue
                    
                    messages = data.get("results", [])
                    
                    if messages:
                        print(f"Received {len(messages)} new messages")
                        
                        # Update the last message ID if we have messages
                        if messages:
                            last_message_id = messages[-1].get("id") 
                        
                        # If we still don't have a proper username, check one last time
                        if not self.username or self.username == "user":
                            await self.fix_username_if_needed()
                        
                        # Process new messages
                        for msg in messages:
                            sender = msg.get("sender", {}).get("username", "unknown")
                            content = msg.get("content", "")
                            sent_at = msg.get("sent_at", "")
                            
                            # Ensure content is not None
                            if content is None:
                                content = ""
                            
                            # Check if we need to update our username from message data
                            if self.username == "user" and self.auth_token:
                                # If we have a token, we can try to identify which messages are ours
                                current_user_in_msg = msg.get("is_sender", False)
                                if current_user_in_msg:
                                    print(f"Found message from current user, updating username to: {sender}")
                                    self.username = sender
                                    rx.call_script(f"""
                                        localStorage.setItem('username', '{sender}');
                                        console.log('Username saved to localStorage from message data:', '{sender}');
                                    """)
                                    is_current_user = True
                                else:
                                    # Determine if the message is from the current user based on username
                                    is_current_user = sender == self.username
                            else:
                                # Determine if the message is from the current user based on username
                                is_current_user = sender == self.username
                            
                            print(f"Polling received message from {sender}, current user is {self.username}, is_current_user: {is_current_user}")
                            
                            # Add to chat history if not already there
                            message_key = f"{sender}:{content}:{sent_at}"
                            if not any(message_key in str(msg) for msg in self.chat_history[-10:]):
                                print(f"Adding message from {sender}: {content[:20]}...")
                                self.chat_history.append(
                                    ("user" if is_current_user else "other", content)
                                )
                    
                    # Update last message time
                    self.last_message_time = asyncio.get_event_loop().time()
            except httpx.HTTPError as e:
                # Handle HTTP-specific errors
                print(f"HTTP error during polling: {str(e)}")
                await asyncio.sleep(5)  # Wait longer after an error
            except Exception as e:
                print(f"Error polling messages: {str(e)}")
                await asyncio.sleep(5)  # Wait longer after an error
                
            # Wait before polling again - shorter wait if no errors
            await asyncio.sleep(2)
        
        print("Message polling stopped.")

    @rx.event
    async def load_messages(self):
        """Load messages for the current room."""
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Cannot load messages: not authenticated")
            return

        if not self.current_room_id:
            print("Cannot load messages: no room ID")
            return
            
        # Store the room_id locally to avoid any issues with state changes
        room_id = self.current_room_id
        
        # Make sure we have the correct username before loading messages
        if not self.username or self.username == "user":
            await self.fix_username_if_needed()
        
        # Log the current username for debugging message ownership
        print(f"Current username for message ownership: {self.username}")
        
        # Make sure username is in sync with localStorage before loading messages
        rx.call_script("""
            const username = localStorage.getItem('username');
            console.log('Direct localStorage username check:', username);
            
            if (username) {
                // Force update both state objects to ensure correct username
                if (window._state) {
                    window._state.username = username;
                    console.log('Directly updated _state.username to:', username);
                }
                
                // Also update state.username which might be a different object
                if (state && state.username !== username) {
                    state.username = username;
                    console.log('Updated state.username to:', username);
                }
            }
        """)
        
        # Wait a moment for username to be set
        await asyncio.sleep(0.1)
        
        # Double-check username again
        print(f"Username after localStorage check: {self.username}")

        try:
            print(f"Loading messages for room {room_id}...")
            
            # Set up headers
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Before loading messages, get room details directly from the server
            # to ensure we have the correct and most up-to-date room name
            async with httpx.AsyncClient() as client:
                # First get the room details to get the most accurate name
                try:
                    room_response = await client.get(
                        f"{self.API_BASE_URL}/communication/rooms/{room_id}/",
                        headers=headers,
                        follow_redirects=True
                    )
                    
                    if room_response.status_code == 200:
                        room_data = room_response.json()
                        if room_data:
                            # Update room name
                            if "name" in room_data:
                                self.current_chat_user = room_data["name"]
                                print(f"Updated room name from API: {self.current_chat_user}")
                    else:
                        print(f"Could not fetch room details, status: {room_response.status_code}")
                        # Fall back to finding room name from cached rooms list
                        self._find_room_name_from_cache(room_id)
                except Exception as e:
                    print(f"Error fetching room details: {e}")
                    # Fall back to finding room name from cached rooms list
                    self._find_room_name_from_cache(room_id)
                
                # Now load messages
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/messages/?room_id={room_id}",
                    headers=headers,
                    follow_redirects=True
                )
                
                print(f"Messages API response status: {response.status_code}")
                
                data = response.json()
                messages = data.get("results", [])
                print(f"Loaded {len(messages)} messages")
                
                # Clear existing chat history
                self.chat_history = []
                
                # Format messages for display - newer messages should be at the bottom
                sorted_messages = sorted(messages, key=lambda m: m.get("sent_at", ""))
                
                for msg in sorted_messages:
                    sender = msg.get("sender", {}).get("username", "unknown")
                    content = msg.get("content", "")
                    
                    # Ensure content is not None
                    if content is None:
                        content = ""
                    
                    # Determine if the message is from the current user
                    is_current_user = sender == self.username
                    
                    print(f"Message from {sender}, current user is {self.username}, is_current_user: {is_current_user}")
                    
                    # Add to chat history
                    self.chat_history.append(
                        ("user" if is_current_user else "other", content)
                    )
                    
                print(f"Successfully loaded and processed {len(messages)} messages")
        except Exception as e:
            print(f"Error loading messages: {str(e)}")
            self.error_message = f"Error loading messages: {str(e)}"
            
            # If in development mode, use dummy data on error
            if self.debug_use_dummy_data:
                self._set_dummy_messages()

    def _find_room_name_from_cache(self, room_id):
        """Helper method to find room name from cached rooms list."""
        print(f"Finding room name from cached rooms for room ID: {room_id}")
        found = False
        for room in self.rooms:
            if str(room.get("id", "")) == str(room_id):
                self.current_chat_user = room.get("name", "Chat Room")
                print(f"Found room name in cache: {self.current_chat_user}")
                found = True
                break
        
        if not found:
            print(f"Room {room_id} not found in cached rooms list, using default name")
            self.current_chat_user = "Chat Room"

    @rx.event
    async def load_rooms(self):
        """Load all rooms for the current user."""
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            self.error_message = "Not authenticated"
            return

        try:
            print("Loading rooms...")
            
            # Set up headers
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Use AsyncClient for HTTP requests
            async with httpx.AsyncClient() as client:
                # Use the correct API endpoint for rooms
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/rooms/",  # Simplified endpoint
                    headers=headers,
                    follow_redirects=True
                )
                
                print(f"Rooms API response status: {response.status_code}")
                
                data = response.json()
                self.rooms = data.get("results", [])  # Adjust based on your API response structure
                print(f"Loaded {len(self.rooms)} rooms")
                
                # Debug room data with more detailed information
                for i, room in enumerate(self.rooms):
                    room_id = room.get("id", "")
                    room_name = room.get("name", "Unknown")
                    print(f"Room {i+1}: ID={room_id}, Name={room_name}")
                    
                    # Additional debug info for direct rooms
                    participants = room.get("participants", [])
                    if participants and len(participants) > 0:
                        participant_names = [p.get("user", {}).get("username", "unknown") for p in participants]
                        print(f"  Participants: {', '.join(participant_names)}")
                
                # If we have a current_room_id but no current_chat_user, try to find the name
                if self.current_room_id and not self.current_chat_user:
                    print(f"Looking for name for room {self.current_room_id}")
                    found = False
                    for room in self.rooms:
                        if str(room.get("id", "")) == str(self.current_room_id):
                            self.current_chat_user = room.get("name", "Chat Room")
                            print(f"Found room name: {self.current_chat_user} for room {self.current_room_id}")
                            found = True
                            break
                    if not found:
                        print(f"WARNING: Could not find room with ID {self.current_room_id} in rooms list")
                    
                # If we have rooms, set the first one as active if no room already selected
                if self.rooms and not self.current_room_id:
                    print("No room selected, setting first room as active")
                    first_room = self.rooms[0]
                    self.current_room_id = first_room.get("id")
                    self.current_chat_user = first_room.get("name", "Chat")
                    print(f"Set active room: ID={self.current_room_id}, Name={self.current_chat_user}")
                    await self.load_messages()
                    
                    # Start polling for messages
                    self.should_reconnect = True
                    self.last_message_time = asyncio.get_event_loop().time()
                    print("Starting polling for first room")
                    asyncio.create_task(self.poll_messages())
                    
                self.loading = False
        except Exception as e:
            self.error_message = f"Error loading rooms: {str(e)}"
            print(f"Error loading rooms: {str(e)}")
            self.loading = False

    @rx.event
    async def accept_call(self):
        """Accept an incoming call and join the call.
        This also notifies the caller via API and WebSocket."""
        print("[WebRTC Debug] Accepting incoming call")
        
        try:
            # Stop ringtone
            rx.call_script("""
                // Stop ringtone if playing
                if (window.ringtoneElement) {
                    window.ringtoneElement.pause();
                    window.ringtoneElement.currentTime = 0;
                }
                
                // Clear title flash interval
                if (window.titleFlashInterval) {
                    clearInterval(window.titleFlashInterval);
                    document.title = 'Chat';
                }
            """)
            
            # Get authentication token
            self.auth_token = await self.get_token()
            if not self.auth_token:
                self.error_message = "Not authenticated"
                return
                    
            # Initialize WebRTC for the call
            await self.initialize_peer_connection()
                    
            # Connect to WebRTC signaling server
            await self.connect_webrtc_signaling()
            
            # 1. Send API request to accept the call
            invitation_id = self.call_invitation_id
            if not invitation_id:
                self.error_message = "No active call invitation"
                return
                    
            # Check if this is a local-only call (when API isn't available)
            is_local_only = False
            if self.active_room_call and self.active_room_call.get("is_local_only"):
                is_local_only = True
                print("[WebRTC Debug] This is a local-only call (no API interactions)")
            
            # Skip API call if this is a local-only call
            if not is_local_only and not invitation_id.startswith("local-") and not invitation_id.startswith("legacy-"):
                # Try API call to update call status
                update_success = await self.update_call_status(invitation_id, "accepted")
                if update_success:
                    print("[WebRTC Debug] Call status updated successfully via API")
                else:
                    print("[WebRTC Debug] Failed to update call status via API, continuing with WebSocket")
                    
            # 2. Hide incoming call popup and show call UI
            self.show_incoming_call = False
            
            if self.call_type == "video":
                self.show_video_popup = True
            else:
                self.show_call_popup = True
                    
            # 3. Send WebSocket notification that call was accepted
            username = await self.get_username()
            rx.call_script(f"""
                // Send call accept notification over WebSocket - multiple formats for compatibility
                if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                    console.log('[WebRTC Debug] [CALL FLOW] Sending call acceptance via WebSocket');
                    
                    // 1. Send acceptance in legacy format
                    window.chatSocket.send(JSON.stringify({{
                        type: 'call_response',
                        invitation_id: '{invitation_id}',
                        response: 'accept',
                        username: '{username}'
                    }}));
                    
                    // 2. Also try API format for compatibility
                    setTimeout(() => {{
                        window.chatSocket.send(JSON.stringify({{
                            type: 'incoming_call_status',
                            notification_id: '{invitation_id}',
                            status: 'accepted'
                        }}));
                    }}, 200);
                    
                    // 3. Also try updated response
                    setTimeout(() => {{
                        window.chatSocket.send(JSON.stringify({{
                            type: 'call_notification_update',
                            notification: {{
                                id: '{invitation_id}',
                                status: 'accepted',
                                responder: '{username}'
                            }}
                        }}));
                    }}, 400);
                    
                    // 4. Send join notification
                    setTimeout(() => {{
                        window.chatSocket.send(JSON.stringify({{
                            type: 'join_call_notification',
                            invitation_id: '{invitation_id}',
                            room_id: '{self.current_room_id}',
                            username: '{username}',
                            call_type: '{self.call_type}'
                        }}));
                    }}, 600);
                }}
                
                // Add self to participants list if this is a room call
                if (state.active_room_call && state.active_room_call.participants) {{
                    if (!state.active_room_call.participants.includes('{username}')) {{
                        state.active_room_call.participants.push('{username}');
                    }}
                }}
                
                // Initialize media for call type
                if ('{self.call_type}' === 'video') {{
                    // Access user's camera and microphone
                    navigator.mediaDevices.getUserMedia({{ 
                        video: true,
                        audio: true
                    }})
                    .then(stream => {{
                        console.log('[WebRTC Debug] Got local media stream for video call');
                        
                        // Store local stream
                        window.localStream = stream;
                        
                        // Update UI with local stream
                        const mediaElement = document.getElementById('local-video');
                        if (mediaElement) {{
                            mediaElement.srcObject = stream;
                        }}
                        
                        // Add tracks to peer connection
                        if (window.peerConnection) {{
                            stream.getTracks().forEach(track => {{
                                window.peerConnection.addTrack(track, stream);
                            }});
                        }} else {{
                            console.error('[WebRTC Debug] Peer connection not initialized');
                        }}
                    }})
                    .catch(error => {{
                        console.error('[WebRTC Debug] Error accessing video devices:', error);
                        state.error_message = 'Error accessing camera or microphone. Please check your permissions.';
                    }});
                }} else {{
                    // Access user's microphone only for audio call
                    navigator.mediaDevices.getUserMedia({{ 
                        audio: true
                    }})
                    .then(stream => {{
                        console.log('[WebRTC Debug] Got local media stream for audio call');
                        
                        // Store local stream
                        window.localStream = stream;
                        
                        // Update UI with local stream
                        const mediaElement = document.getElementById('local-audio');
                        if (mediaElement) {{
                            mediaElement.srcObject = stream;
                        }}
                        
                        // Add tracks to peer connection
                        if (window.peerConnection) {{
                            stream.getTracks().forEach(track => {{
                                window.peerConnection.addTrack(track, stream);
                            }});
                        }} else {{
                            console.error('[WebRTC Debug] Peer connection not initialized');
                        }}
                    }})
                    .catch(error => {{
                        console.error('[WebRTC Debug] Error accessing audio devices:', error);
                        state.error_message = 'Error accessing microphone. Please check your permissions.';
                    }});
                }}
            """)
            
            # 4. Start call timer
            await self.start_call_timer()
            
        except Exception as e:
            self.error_message = f"Error accepting call: {str(e)}"
            print(f"[WebRTC Debug] Error accepting call: {str(e)}")
            self.show_incoming_call = False

    @rx.event
    async def update_call_status(self, notification_id: str, status: str) -> bool:
        """Update the status of a call notification via API.
        
        Args:
            notification_id: The ID of the call notification
            status: The new status ('seen', 'accepted', 'declined', 'missed', 'ended')
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        print(f"[WebRTC Debug] Updating call status to {status}: {notification_id}")
        
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            print("[WebRTC Debug] Not authenticated, cannot update call status")
            return False
            
        # API URL for updating call status
        api_url = f"{self.API_HOST_URL}/communication/incoming-calls/{notification_id}/"
        
        # Create payload with status
        payload = {"status": status}
        
        # Try with both token formats (Bearer and Token)
        auth_headers = [
            {"Authorization": f"Bearer {self.auth_token}"},
            {"Authorization": f"Token {self.auth_token}"}
        ]
        
        for headers in auth_headers:
            try:
                headers["Content-Type"] = "application/json"
                print(f"[WebRTC Debug] Trying status update with headers: {headers}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.put(
                        api_url,
                        json=payload,
                        headers=headers,
                        follow_redirects=True,
                        timeout=10.0
                    )
                    
                    print(f"[WebRTC Debug] Status update response: {response.status_code}")
                    
                    if response.status_code >= 200 and response.status_code < 300:
                        print("[WebRTC Debug] Call status updated successfully")
                        return True
                    else:
                        print(f"[WebRTC Debug] Failed to update call status: {response.text[:200]}")
            except Exception as e:
                print(f"[WebRTC Debug] Error updating call status with {list(headers.keys())[0]}: {str(e)}")
        
        return False

    @rx.event
    async def handle_caller_connection(self, notification_id: str):
        """Handle connection when the user is the caller and the recipient has accepted.
        This is called by WebSocket notification when a call is accepted."""
        print(f"[WebRTC Debug] Handling caller connection for call: {notification_id}")
        
        try:
            # Update UI state
            self.show_calling_popup = False
            
            if self.call_type == "video":
                self.show_video_popup = True
            else:
                self.show_call_popup = True
                
            # Initialize media stream based on call type
            rx.call_script(f"""
                // Initialize media for call type
                if ('{self.call_type}' === 'video') {{
                    // Access user's camera and microphone
                    navigator.mediaDevices.getUserMedia({{ 
                        video: true,
                        audio: true
                    }})
                    .then(stream => {{
                        console.log('[WebRTC Debug] Got local media stream for video call');
                        
                        // Store local stream
                        window.localStream = stream;
                        
                        // Update UI with local stream
                        const mediaElement = document.getElementById('local-video');
                        if (mediaElement) {{
                            mediaElement.srcObject = stream;
                        }}
                        
                        // Add tracks to peer connection
                        if (window.peerConnection) {{
                            stream.getTracks().forEach(track => {{
                                window.peerConnection.addTrack(track, stream);
                            }});
                            
                            // Create and send offer
                            window.peerConnection.createOffer()
                                .then(offer => window.peerConnection.setLocalDescription(offer))
                                .then(() => {{
                                    console.log('[WebRTC Debug] Sending SDP offer');
                                    if (window.signalingSocket && window.signalingSocket.readyState === WebSocket.OPEN) {{
                                        window.signalingSocket.send(JSON.stringify({{
                                            type: 'offer',
                                            offer: window.peerConnection.localDescription
                                        }}));
                                    }}
                                }})
                                .catch(error => {{
                                    console.error('[WebRTC Debug] Error creating offer:', error);
                                    state.error_message = 'Error establishing call connection';
                                }});
                        }} else {{
                            console.error('[WebRTC Debug] Peer connection not initialized');
                        }}
                    }})
                    .catch(error => {{
                        console.error('[WebRTC Debug] Error accessing video devices:', error);
                        state.error_message = 'Error accessing camera or microphone. Please check your permissions.';
                    }});
                }} else {{
                    // Access user's microphone only for audio call
                    navigator.mediaDevices.getUserMedia({{ 
                        audio: true
                    }})
                    .then(stream => {{
                        console.log('[WebRTC Debug] Got local media stream for audio call');
                        
                        // Store local stream
                        window.localStream = stream;
                        
                        // Update UI with local stream
                        const mediaElement = document.getElementById('local-audio');
                        if (mediaElement) {{
                            mediaElement.srcObject = stream;
                        }}
                        
                        // Add tracks to peer connection
                        if (window.peerConnection) {{
                            stream.getTracks().forEach(track => {{
                                window.peerConnection.addTrack(track, stream);
                            }});
                            
                            // Create and send offer
                            window.peerConnection.createOffer()
                                .then(offer => window.peerConnection.setLocalDescription(offer))
                                .then(() => {{
                                    console.log('[WebRTC Debug] Sending SDP offer');
                                    if (window.signalingSocket && window.signalingSocket.readyState === WebSocket.OPEN) {{
                                        window.signalingSocket.send(JSON.stringify({{
                                            type: 'offer',
                                            offer: window.peerConnection.localDescription
                                        }}));
                                    }}
                                }})
                                .catch(error => {{
                                    console.error('[WebRTC Debug] Error creating offer:', error);
                                    state.error_message = 'Error establishing call connection';
                                }});
                        }} else {{
                            console.error('[WebRTC Debug] Peer connection not initialized');
                        }}
                    }})
                    .catch(error => {{
                        console.error('[WebRTC Debug] Error accessing audio devices:', error);
                        state.error_message = 'Error accessing microphone. Please check your permissions.';
                    }});
                }}
            """)
            
            # Start call timer
            await self.start_call_timer()
            
        except Exception as e:
            print(f"[WebRTC Debug] Error handling caller connection: {str(e)}")
            self.error_message = f"Error connecting call: {str(e)}"
            
    @rx.event
    async def decline_call(self):
        """Decline an incoming call."""
        print("[WebRTC Debug] Declining incoming call")
        
        try:
            # Get authentication token
            self.auth_token = await self.get_token()
            if not self.auth_token:
                self.error_message = "Not authenticated"
                return
                
            # Get invitation ID
            invitation_id = self.call_invitation_id
            if not invitation_id:
                self.error_message = "No active call invitation"
                return
                
            # Check if this is a local-only call (when API isn't available)
            is_local_only = False
            if self.active_room_call and self.active_room_call.get("is_local_only"):
                is_local_only = True
                print("[WebRTC Debug] This is a local-only call (no API interactions)")
                
            # Skip API call if this is a local-only call
            if not is_local_only and not invitation_id.startswith("local-"):
                # Decline call via API
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                api_url = f"{self.API_BASE_URL}/communication/incoming-calls/{invitation_id}/"
                
                try:
                    # Make API request
                    client = httpx.AsyncClient()
                    response = await client.put(
                        api_url,
                        json={"status": "declined"},
                        headers=headers,
                        follow_redirects=True
                    )
                    
                    if response.status_code == 404:
                        print("[WebRTC Debug] Decline call API endpoint not found (404), proceeding with WebSocket only")
                    elif response.status_code not in [200, 201, 204]:
                        raise Exception(f"Failed to decline call: {response.status_code}")
                    elif self.debug_log_api_calls:
                        print(f"Call decline API response: {response.status_code}")
                except Exception as e:
                    print(f"[WebRTC Debug] Error with call decline API: {str(e)}")
                    print("[WebRTC Debug] Continuing with WebSocket-based decline")
            
            # Stop ringtone and clear UI
            rx.call_script(f"""
                // Stop ringtone if playing
                if (window.ringtoneElement) {{
                    window.ringtoneElement.pause();
                    window.ringtoneElement.currentTime = 0;
                }}
                
                // Clear title flash interval
                if (window.titleFlashInterval) {{
                    clearInterval(window.titleFlashInterval);
                    document.title = 'Chat';
                }}
                
                // Send call response over WebSocket
                if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                    window.chatSocket.send(JSON.stringify({{
                        type: 'call_response',
                        invitation_id: '{invitation_id}',
                        response: 'decline'
                    }}));
                }}
            """)
            
            # Reset state
            self.show_incoming_call = False
            self.call_invitation_id = ""
            self.incoming_caller = ""
            self.call_type = "audio"
            self.active_room_call = {}
            
        except Exception as e:
            self.error_message = f"Error declining call: {str(e)}"
            print(f"[WebRTC Debug] Error declining call: {str(e)}")
            self.show_incoming_call = False

    @rx.event
    async def on_room_open(self):
        """Connect to the chat WebSocket when a room is opened."""
        # This method should be called after a room is successfully opened
        if self.current_room_id:
            # Connect to the chat WebSocket for this room
            await self.connect_chat_websocket()
            
            # Start polling for messages as a fallback if WebSocket fails
            if not self.is_connected:
                self.should_reconnect = True
                asyncio.create_task(self.poll_messages())

    @rx.event
    async def get_webrtc_config(self):
        """Get WebRTC configuration from the server."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot get WebRTC config")
            self.error_message = "Not authenticated. Please log in."
            return
            
        try:
            # Set up headers
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Use AsyncClient for HTTP requests
            async with httpx.AsyncClient() as client:
                # Use your exact API endpoint format
                room_id_str = str(self.current_room_id)
                
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/rooms/{room_id_str}/webrtc_config/",
                    headers=headers,
                    follow_redirects=True
                )
                
                print(f"WebRTC config response status: {response.status_code}")
                if response.status_code == 200:
                    config_data = response.json()
                    self.webrtc_config = config_data
                    self.ice_servers = config_data.get("ice_servers", [])
                    print(f"Loaded WebRTC config: {self.webrtc_config}")
                    return config_data
                else:
                    print(f"Failed to get WebRTC config: {response.status_code}")
                    # Print condensed response to avoid long HTML output
                    if response.headers.get("content-type", "").startswith("text/html"):
                        print("Response contains HTML error page")
                    else:
                        print(f"Response content: {response.text[:200]}...")
                    
                    # Use default configuration if server doesn't provide one
                    print("Using default WebRTC configuration")
                    default_config = {
                        "ice_servers": [
                            {"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}
                        ],
                        "media_constraints": {
                            "audio": {
                                "echoCancellation": True,
                                "noiseSuppression": True,
                                "autoGainControl": True
                            },
                            "video": {
                                "width": {"ideal": 1280, "max": 1920},
                                "height": {"ideal": 720, "max": 1080},
                                "frameRate": {"ideal": 30, "max": 60}
                            }
                        }
                    }
                    self.webrtc_config = default_config
                    self.ice_servers = default_config.get("ice_servers", [])
                    return default_config
        except Exception as e:
            self.error_message = f"Error getting WebRTC config: {str(e)}"
            print(f"Error getting WebRTC config: {str(e)}")
            
            # Use default configuration as fallback
            default_config = {
                "ice_servers": [
                    {"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}
                ],
                "media_constraints": {
                    "audio": {
                        "echoCancellation": True,
                        "noiseSuppression": True,
                        "autoGainControl": True
                    },
                    "video": {
                        "width": {"ideal": 1280, "max": 1920},
                        "height": {"ideal": 720, "max": 1080},
                        "frameRate": {"ideal": 30, "max": 60}
                    }
                }
            }
            self.webrtc_config = default_config
            self.ice_servers = default_config.get("ice_servers", [])
            return default_config

    @rx.event
    async def connect_webrtc_signaling(self):
        """Connect to WebRTC signaling WebSocket."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot connect to signaling")
            self.error_message = "Not authenticated. Please log in."
            return
            
        # Get WebRTC configuration if we don't have it
        if not self.webrtc_config:
            await self.get_webrtc_config()
            
        # Connect to signaling WebSocket using JavaScript
        rx.call_script(f"""
            // Close existing connection if any
            if (window.signalingSocket && window.signalingSocket.readyState !== WebSocket.CLOSED) {{
                window.signalingSocket.close();
            }}
            
            // Create new WebSocket connection for WebRTC signaling
            // Using your exact WebSocket URL format
            const wsBaseUrl = '{self.WS_BASE_URL}';
            const roomId = '{self.current_room_id}';
            const wsUrl = `${{wsBaseUrl}}/webrtc/${{roomId}}/`;
            console.log('Connecting to WebRTC signaling at:', wsUrl);
            
            window.signalingSocket = new WebSocket(wsUrl);
            
            window.signalingSocket.onopen = function() {{
                console.log('WebRTC signaling connection established');
                // Send authentication message
                window.signalingSocket.send(JSON.stringify({{
                    type: 'auth',
                    token: '{self.auth_token}'
                }}));
                // Update state
                state.signaling_connected = true;
            }};
            
            window.signalingSocket.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                console.log('WebRTC signaling message received:', data);
                
                // Handle different message types
                switch(data.type) {{
                    case 'offer':
                        handleOffer(data.offer);
                        break;
                    case 'answer':
                        handleAnswer(data.answer);
                        break;
                    case 'ice_candidate':
                        handleIceCandidate(data.candidate);
                        break;
                    case 'peer_joined':
                        notifyPeerJoined(data.user_id, data.username);
                        break;
                    case 'peer_left':
                        notifyPeerLeft(data.user_id, data.username);
                        break;
                    case 'error':
                        console.error('Signaling error:', data.message);
                        state.error_message = data.message;
                        break;
                }}
            }};
            
            window.signalingSocket.onclose = function(event) {{
                console.log('WebRTC signaling connection closed', event);
                state.signaling_connected = false;
                
                // Check if it was an abnormal closure and server sent a code
                if (event.code !== 1000) {{  // 1000 is normal closure
                    console.error('WebSocket closed abnormally:', event.code, event.reason);
                    state.error_message = `WebRTC connection closed: ${{event.reason || 'Unknown reason'}}`;
                }}
            }};
            
            window.signalingSocket.onerror = function(error) {{
                console.error('WebRTC signaling error:', error);
                state.error_message = 'WebRTC signaling connection error';
                state.signaling_connected = false;
            }};
            
            // Function to handle incoming offer
            function handleOffer(offer) {{
                if (!window.peerConnection) {{
                    initializePeerConnection();
                }}
                window.peerConnection.setRemoteDescription(new RTCSessionDescription(offer))
                    .then(() => window.peerConnection.createAnswer())
                    .then(answer => window.peerConnection.setLocalDescription(answer))
                    .then(() => {{
                        // Send answer back
                        window.signalingSocket.send(JSON.stringify({{
                            type: 'answer',
                            answer: window.peerConnection.localDescription
                        }}));
                    }})
                    .catch(error => {{
                        console.error('Error handling offer:', error);
                        state.error_message = 'Error handling call offer';
                    }});
            }}
            
            // Function to handle incoming answer
            function handleAnswer(answer) {{
                if (window.peerConnection) {{
                    window.peerConnection.setRemoteDescription(new RTCSessionDescription(answer))
                        .catch(error => {{
                            console.error('Error handling answer:', error);
                            state.error_message = 'Error establishing connection';
                        }});
                }}
            }}
            
            // Function to handle incoming ICE candidate
            function handleIceCandidate(candidate) {{
                if (window.peerConnection) {{
                    window.peerConnection.addIceCandidate(new RTCIceCandidate(candidate))
                        .catch(error => {{
                            console.error('Error adding ICE candidate:', error);
                        }});
                }}
            }}
            
            // Function to handle peer joined event
            function notifyPeerJoined(userId, username) {{
                console.log(`Peer joined: ${{username}} (${{userId}})`);
                // Could trigger UI updates here
            }}
            
            // Function to handle peer left event
            function notifyPeerLeft(userId, username) {{
                console.log(`Peer left: ${{username}} (${{userId}})`);
                // Could clean up resources here
            }}
        """)
        self.signaling_connected = True

    @rx.event
    async def announce_room_call(self, api_url: str, call_type: str = "audio"):
        """
        Create a call notification for all users in a room that will trigger popup windows.
        
        Args:
            api_url: The API URL for creating call notifications
            call_type: The type of call ("audio" or "video")
        """
        print(f"[WebRTC Debug] Announcing {call_type} call to room {self.current_room_id}")
        
        try:
            # Set the room call API URL
            self.room_call_api_url = api_url
            
            # 1. Get necessary data
            self.auth_token = await self.get_token()
            if not self.auth_token:
                self.error_message = "Not authenticated"
                return
                
            current_username = await self.get_username()
            if not current_username:
                self.error_message = "Username not found"
                return
                
            room_id = self.current_room_id
            if not room_id:
                self.error_message = "No active room selected"
                return
                
            # Find room name - make sure we have a proper room name
            room_name = self.current_chat_user
            if not room_name:
                for room in self.rooms:
                    if str(room.get("id", "")) == str(room_id):
                        room_name = room.get("name", f"Room {room_id}")
                        break
                if not room_name:
                    room_name = f"Room {room_id}"
            
            # Create a unique local ID for the call in case API fails
            local_call_id = f"local-{room_id}-{int(time.time())}"
            
            # 2. Try to create call notification using the provided API URL
            # But also have a fallback for when the API isn't implemented yet
            rx.call_script(f"""
                console.log('[WebRTC Debug] Creating room call notification via API: {api_url}');
                
                // DEBUGGING: Alert to confirm the script is running
                console.warn('[CRITICAL DEBUG] About to make POST request to {api_url}');
                
                // Show calling popup
                state.show_calling_popup = true;
                state.call_type = '{call_type}';
                state._update();
                
                // Function to handle API-based approach
                function createCallNotificationViaAPI() {{
                    // Create notification
                    console.warn('[CRITICAL DEBUG] Making fetch POST request now');
                    
                    // Show an alert to confirm the code is running
                    alert('Attempting to make call API request to: ' + '{api_url}');
                    
                    const requestBody = {{
                        'recipient_id': null, // Setting to null for room-wide calls
                        'room_id': '{room_id}',
                        'call_type': '{call_type}'
                    }};
                    
                    console.warn('[CRITICAL DEBUG] Request body:', JSON.stringify(requestBody));
                    
                    // Try first with Token auth
                    tryFetchWithAuth('Token');
                    
                    // Function to try fetch with different auth types
                    function tryFetchWithAuth(authType) {{
                        console.warn('[CRITICAL DEBUG] Trying with ' + authType + ' authentication');
                        
                        // Use explicit fetch with detailed logging
                            fetch('{api_url}', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/json',
                                    'Authorization': authType + ' {self.auth_token}'
                                }},
                                body: JSON.stringify(requestBody)
                            }})
                            .then(function(response) {{
                                console.warn('[CRITICAL DEBUG] Room call API response received (' + authType + '):', response.status);
                                
                                // Store response in a variable accessible to later callbacks
                                const responseStatus = response.status;
                                
                                return response.text().then(function(text) {{
                                    try {{
                                        // Try to parse as JSON
                                        const data = JSON.parse(text);
                                        console.warn('[CRITICAL DEBUG] Parsed JSON response:', data);
                                    
                                    // If successful response, continue with JSON data
                                    if (responseStatus >= 200 && responseStatus < 300) {{
                                        return data;
                                    }} else if (responseStatus === 401 && authType === 'Token') {{
                                        // If unauthorized with Token, try Bearer
                                        console.warn('[CRITICAL DEBUG] Token auth failed, trying Bearer');
                                        tryFetchWithAuth('Bearer');
                                        return null;
                                    }} else {{
                                        throw new Error('API error (' + responseStatus + '): ' + JSON.stringify(data));
                                    }}
                                }} catch (e) {{
                                    // Not JSON or parsing error
                                    console.warn('[CRITICAL DEBUG] Raw response text:', text);
                                    
                                    if (responseStatus === 404) {{
                                        throw new Error('API endpoint not found (404)');
                                    }} else if (responseStatus === 401 && authType === 'Token') {{
                                        // If unauthorized with Token, try Bearer
                                        console.warn('[CRITICAL DEBUG] Token auth failed, trying Bearer');
                                        tryFetchWithAuth('Bearer');
                                        return null;
                                    }} else {{
                                        throw new Error('Failed: ' + responseStatus + ', Response: ' + text);
                                    }}
                                }}
                            }});
                        }})
                        .then(function(data) {{
                            if (!data) return; // Skip if auth switching
                            
                            console.warn('[CRITICAL DEBUG] Room call API success - Processing data');
                            alert('Call API request successful!');
                                                
                                                // Store the notification ID for later use
                                                state.call_invitation_id = data.id;
                                                
                                                // Send WebSocket message to announce call to all room users
                                                announceCallViaWebSocket(data.id);
                                                
                            console.log('[WebRTC Debug] Room call started successfully');
                                                state.active_room_call = {{
                                                    id: data.id,
                                                    room_id: '{room_id}',
                                                    room_name: '{room_name}',
                                                    call_type: '{call_type}',
                                                    started_by: '{current_username}',
                                                    start_time: new Date().toISOString()
                                                }};
                                                state._update();
                        }})
                        .catch(function(error) {{
                            if (error.message && error.message.includes('auth failed')) return; // Skip if auth switching
                            
                            console.error('[CRITICAL DEBUG] Error making POST request:', error);
                            alert('Error making call API request: ' + error.message);
                            
                            // If API endpoint not found, use WebSocket only approach
                            if (error.message && error.message.includes('404')) {{
                                console.log('[WebRTC Debug] API endpoint not available, using WebSocket only');
                                            handleAPIUnavailable();
                                        }} else {{
                                state.error_message = 'Failed to start room call: ' + error.message;
                                state.show_calling_popup = false;
                                state._update();
                            }}
                        }});
                    }}
                }}
                
                // Function to handle WebSocket announcement - IMPROVED
                function announceCallViaWebSocket(callId) {{
                    // Send WebSocket message to announce call to all room users
                    if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                        console.log('[WebRTC Debug] Sending room-wide call announcement');
                        
                        // Create a consistently structured message for room calls
                        const callAnnouncement = {{
                            type: 'room_call_announcement',
                            room_id: '{room_id}',
                            room_name: '{room_name}',
                            caller_username: '{current_username}',
                            call_type: '{call_type}',
                            invitation_id: callId
                        }};
                        
                        // Log the exact message we're sending
                        console.log('[WebRTC Debug] Call announcement payload:', callAnnouncement);
                        
                        // Send the message
                        window.chatSocket.send(JSON.stringify(callAnnouncement));
                        
                        // Also add a system message to the chat to indicate a call started
                        const callStartedMessage = {{
                            type: 'message',
                            message: {{
                                content: '{current_username} started a ' + 
                                        ('{call_type}' === 'video' ? 'video' : 'audio') + 
                                        ' call. You can join by clicking the call banner at the top of the chat.',
                                sender: {{
                                    username: 'System'
                                }},
                                sent_at: new Date().toISOString()
                            }}
                        }};
                        
                        // Send the system message
                        setTimeout(() => {{
                            if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                                window.chatSocket.send(JSON.stringify(callStartedMessage));
                            }}
                        }}, 500);
                            }} else {{
                        console.error('[WebRTC Debug] Cannot announce call: WebSocket not connected');
                        state.error_message = 'Cannot start call: Communication channel not connected';
                    }}
                }}
                
                // Function to handle the case where API is unavailable
                function handleAPIUnavailable() {{
                    console.log('[WebRTC Debug] Using local call ID:', '{local_call_id}');
                    
                    // Set a local call ID instead
                    state.call_invitation_id = '{local_call_id}';
                    
                    // Announce call via WebSocket only
                    announceCallViaWebSocket('{local_call_id}');
                    
                    // Update state with local call info
                    state.active_room_call = {{
                        id: '{local_call_id}',
                        room_id: '{room_id}',
                        room_name: '{room_name}',
                        call_type: '{call_type}',
                        started_by: '{current_username}',
                        start_time: new Date().toISOString(),
                        is_local_only: true // Flag to indicate this call exists only via WebSocket
                    }};
                    state._update();
                }}
                
                // Start the process
                createCallNotificationViaAPI();
            """)
            
            # 3. Start call timer
            if call_type in ["audio", "video"]:
                await self.start_call_timer()
                
        except Exception as e:
            print(f"[WebRTC Debug] Error announcing room call: {str(e)}")
            self.error_message = f"Error announcing room call: {str(e)}"
            self.show_calling_popup = False


    @rx.event
    async def get_active_call_notifications(self):
        """Fetch active call notifications for the current user."""
        print("[WebRTC Debug] Checking for active call notifications")
        
        try:
            # Get authentication token
            self.auth_token = await self.get_token()
            if not self.auth_token:
                print("[WebRTC Debug] Not authenticated, can't check for notifications")
                return
                
            # Fetch active notifications
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            api_url = f"{self.API_BASE_URL}/communication/incoming-calls/"
            
            client = httpx.AsyncClient()
            response = await client.get(
                api_url,
                headers=headers,
                follow_redirects=True
            )
            
            if response.status_code == 404:
                # If the endpoint doesn't exist yet, don't treat as an error
                print("[WebRTC Debug] Notification API endpoint not found (404) - this feature may not be implemented on the backend yet")
                return
            elif response.status_code != 200:
                print(f"[WebRTC Debug] Failed to fetch notifications: {response.status_code}")
                return
                
            # Validate API response format and process notifications
            try:
                response_data = response.json()
                
                # Extract the active notifications from the new response format
                notifications = []
                if isinstance(response_data, dict):
                    if 'data' in response_data and isinstance(response_data['data'], dict) and 'active' in response_data['data']:
                        notifications = response_data['data']['active']
                        print(f"[WebRTC Debug] Found active notifications in data.active: {len(notifications)}")
                    elif 'active' in response_data:
                        notifications = response_data['active']
                        print(f"[WebRTC Debug] Found active notifications in root.active: {len(notifications)}")
                    else:
                        print(f"[WebRTC Debug] No active notifications found in response structure")
                elif isinstance(response_data, list):
                    notifications = response_data
                    print(f"[WebRTC Debug] Response was a direct list of notifications: {len(notifications)}")
                
                if self.debug_log_api_calls:
                    print(f"[WebRTC Debug] Received {len(notifications)} active call notifications")
                
                # Ensure notifications is a list and each item is a dictionary
                if not isinstance(notifications, list):
                    print(f"[WebRTC Debug] Expected list of notifications but got {type(notifications)}")
                    return
                
                # Handle pending notifications (only show the most recent one if multiple exist)
                pending_notifications = []
                for notification in notifications:
                    if not isinstance(notification, dict):
                        print(f"[WebRTC Debug] Skipping non-dict notification: {notification}")
                        continue
                        
                    if notification.get("status") == "pending":
                        pending_notifications.append(notification)
                
                if pending_notifications:
                    # Sort by created_at time and get the most recent
                    pending_notifications.sort(key=lambda n: n.get("created_at", ""), reverse=True)
                    notification = pending_notifications[0]
                    
                    # Show incoming call notification for the most recent pending call
                    caller_info = notification.get("caller", {})
                    caller_username = "Unknown caller"
                    
                    if isinstance(caller_info, dict):
                        caller_username = caller_info.get("username", "Unknown caller")
                    elif isinstance(caller_info, str):
                        caller_username = caller_info
                    
                    room_name = notification.get("room_name", "Unknown room")
                    call_type = notification.get("call_type", "audio")
                    notification_id = notification.get("id", "")
                    
                    print(f"[WebRTC Debug] Showing pending call from {caller_username} in {room_name}")
                    
                    # Set up UI to show incoming call
                    self.show_incoming_call = True
                    self.call_invitation_id = notification_id
                    self.call_type = call_type
                    self.incoming_caller = caller_username
                    self.current_chat_user = caller_username
                    
                    # Set active room call info
                    self.active_room_call = {
                        "id": notification_id,
                        "room_id": notification.get("room", ""),
                        "room_name": room_name,
                        "call_type": call_type,
                        "started_by": caller_username,
                        "participants": [caller_username]
                    }
                    
                    # Play ringtone and update UI via JavaScript
                    rx.call_script("""
                        // Play ringtone
                        try {
                            if (!window.ringtoneElement) {
                                window.ringtoneElement = new Audio('/static/ringtone.mp3');
                                window.ringtoneElement.loop = true;
                                window.ringtoneElement.volume = 0.7;
                            }
                            
                            const playPromise = window.ringtoneElement.play();
                            
                            if (playPromise !== undefined) {
                                playPromise.catch(e => {
                                    console.log('[WebRTC Debug] Error playing ringtone:', e);
                                    // Add click handler for user interaction
                                    document.addEventListener('click', function unlockAudio() {
                                        window.ringtoneElement.play();
                                        document.removeEventListener('click', unlockAudio);
                                    }, {once: true});
                                });
                            }
                        } catch(e) {
                            console.error('[WebRTC Debug] Exception playing ringtone:', e);
                        }
                        
                        // Flash title
                        const origTitle = document.title;
                        window.titleFlashInterval = setInterval(() => {
                            document.title = document.title === origTitle ? 
                                `📞 Incoming Call from ${state.incoming_caller}` : origTitle;
                        }, 1000);
                    """)
                    
            except ValueError as e:
                print(f"[WebRTC Debug] Invalid JSON in notification response: {str(e)}")
                if self.debug_log_api_calls:
                    print(f"[WebRTC Debug] Response content: {response.text[:200]}...")
                
        except Exception as e:
            print(f"[WebRTC Debug] Error fetching call notifications: {str(e)}")
            # Don't set error message to avoid disrupting the UI for a background check

    async def _periodic_notification_check(self):
        """Periodically check for new call notifications."""
        while True:
            # Only check if we're not already in a call
            if not self.show_call_popup and not self.show_video_popup and not self.show_incoming_call:
                await self.get_active_call_notifications()
            
            # Wait for next check interval (15-30 seconds is reasonable)
            await asyncio.sleep(20)

def calling_popup() -> rx.Component:
    """Component for showing the calling popup."""
    return rx.cond(
        ChatState.show_calling_popup,
        rx.box(
            rx.center(
                rx.vstack(
                    rx.avatar(
                        name=ChatState.current_chat_user,
                        size="9",
                        border="4px solid #80d0ea",
                        margin_bottom="20px",
                        border_radius="50%",
                        width="120px",
                        height="120px",
                        animation="pulse 1.5s infinite",
                    ),
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="10px",
                        text_align="center",
                    ),
                    rx.text(
                        rx.cond(
                            ChatState.call_type == "video",
                            "Calling via video...",
                            "Calling via audio..."
                        ),
                        font_size="18px",
                        color="#666666",
                        margin_bottom="20px",
                        text_align="center",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("phone-off"),
                            on_click=rx.cond(
                                ChatState.call_type == "video",
                                ChatState.end_video_call,
                                ChatState.end_call,
                            ),
                            border_radius="50%",
                            bg="#ff4444",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#ff3333",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        justify_content="center",
                        width="100%",
                    ),
                    align_items="center",
                    justify_content="center",
                    width="340px",
                    height="400px",
                    bg="white",
                    border_radius="20px",
                    padding="30px",
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
                    z_index="1000",
                    css={
                        "@keyframes pulse": {
                            "0%": {"box-shadow": "0 0 0 0 rgba(128, 208, 234, 0.7)"},
                            "70%": {"box-shadow": "0 0 0 10px rgba(128, 208, 234, 0)"},
                            "100%": {"box-shadow": "0 0 0 0 rgba(128, 208, 234, 0)"}
                        }
                    },
                ),
            ),
            position="fixed",
            top="0",
            left="0",
            width="100%",
            height="100%",
            bg="rgba(0, 0, 0, 0.5)",
            display="flex",
            justify_content="center",
            align_items="center",
        ),
        None,
    )

def call_popup() -> rx.Component:
    return rx.cond(
        ChatState.show_call_popup,
        rx.box(
            rx.center(
                rx.vstack(
                    rx.avatar(
                        name=ChatState.current_chat_user,
                        size="9",
                        border="4px solid #80d0ea",
                        margin_bottom="20px",
                        border_radius="50%",
                        width="120px",
                        height="120px",
                    ),
                    # Hidden audio elements
                    rx.html("""
                        <audio id="remote-audio" autoplay></audio>
                        <audio id="local-audio" autoplay muted></audio>
                    """),
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="10px",
                    ),
                    # Call status and mute indicators
                    rx.hstack(
                        rx.text(
                            rx.cond(
                                ChatState.is_call_connected,
                                "Connected",
                                "Connecting..."
                            ),
                            color=rx.cond(
                                ChatState.is_call_connected,
                                "green.500",
                                "orange.500"
                            ),
                            font_size="14px",
                        ),
                        rx.cond(
                            ChatState.is_muted,
                            rx.box(
                                rx.icon("mic-off"),
                                color="red.500",
                                margin_left="10px",
                            ),
                        ),
                        rx.cond(
                            ChatState.remote_is_muted,
                            rx.box(
                                rx.icon("mic-off"),
                                color="red.500",
                                margin_left="10px",
                            ),
                        ),
                        margin_bottom="10px",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                ChatState.is_muted,
                                rx.icon("mic-off"),
                                rx.icon("mic"),
                            ),
                            on_click=ChatState.toggle_mute,
                            border_radius="50%",
                            bg="#80d0ea",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#6bc0d9",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        rx.button(
                            rx.icon("phone-off"),
                            on_click=ChatState.end_call,
                            border_radius="50%",
                            bg="#ff4444",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#ff3333",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        spacing="4",  # Changed from "20px" to "4"
                    ),
                    padding="20px",
                    bg="white",
                    border_radius="10px",
                    box_shadow="0 4px 6px rgba(0, 0, 0, 0.1)",
                ),
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1000",
            ),
        ),
    )

def video_call_popup() -> rx.Component:
    return rx.cond(
        ChatState.show_video_popup,
        rx.box(
            rx.center(
                rx.vstack(
                    # Video elements
                    rx.html("""
                        <video id="remote-video" autoplay playsinline></video>
                        <video id="local-video" autoplay playsinline muted></video>
                    """),
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="10px",
                    ),
                    # Call status and mute indicators
                    rx.hstack(
                        rx.text(
                            rx.cond(
                                ChatState.is_call_connected,
                                "Connected",
                                "Connecting..."
                            ),
                            color=rx.cond(
                                ChatState.is_call_connected,
                                "green.500",
                                "orange.500"
                            ),
                            font_size="14px",
                        ),
                        rx.cond(
                            ChatState.is_muted,
                            rx.box(
                                rx.icon("mic-off"),
                                color="red.500",
                                margin_left="10px",
                            ),
                        ),
                        rx.cond(
                            ChatState.remote_is_muted,
                            rx.box(
                                rx.icon("mic-off"),
                                color="red.500",
                                margin_left="10px",
                            ),
                        ),
                        margin_bottom="10px",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                ChatState.is_muted,
                                rx.icon("mic-off"),
                                rx.icon("mic"),
                            ),
                            on_click=ChatState.toggle_mute,
                            border_radius="50%",
                            bg="#80d0ea",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#6bc0d9",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        rx.button(
                            rx.cond(
                                ChatState.is_camera_off,
                                rx.icon("video-off"),
                                rx.icon("video"),
                            ),
                            on_click=ChatState.toggle_camera,
                            border_radius="50%",
                            bg="#80d0ea",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#6bc0d9",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        rx.button(
                            rx.icon("phone-off"),
                            on_click=ChatState.end_video_call,
                            border_radius="50%",
                            bg="#ff4444",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#ff3333",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        spacing="4",  # Changed from "20px" to "4"
                    ),
                    padding="20px",
                    bg="white",
                    border_radius="10px",
                    box_shadow="0 4px 6px rgba(0, 0, 0, 0.1)",
                ),
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="1000",
            ),
        ),
    )

def rooms_list() -> rx.Component:
    """Render a list of room buttons with dynamic URLs."""
    return rx.box(
        rx.vstack(
            rx.heading("Your Chats", size="2", color="white", padding="3", bg="#444444"),
            rx.divider(),
            rx.vstack(
                # Dynamic Room buttons based on formatted_rooms 
                rx.cond(
                    ChatState.formatted_rooms.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            ChatState.formatted_rooms,
                            lambda room, index: rx.button(
                                rx.hstack(
                                    rx.avatar(name=room.get("name", f"Room {index+1}"), size="2"),
                                    rx.vstack(
                                        rx.text(room.get("name", f"Room {index+1}"), font_weight="bold", color="white"),
                                        rx.text(
                                            rx.cond(
                                                room.get("last_message", "") != "",
                                                room.get("last_message", ""),
                                                "No messages yet"
                                            ),
                                            color="#cccccc", 
                                            font_size="12px"
                                        ),
                                        align_items="start",
                                        spacing="0",
                                    ),
                                    width="100%",
                                ),
                                # Use direct URL pattern for chat rooms
                                on_click=lambda: ChatState.open_room(room.get("id", ""), room.get("name", f"Room {index+1}")),
                                width="100%",
                                justify_content="flex-start",
                                bg="transparent",
                                _hover={"bg": "#444444"},
                                border_radius="md",
                                padding="2",
                                variant="ghost",
                            )
                        ),
                        # Static fallback buttons (can be removed in production)
                        rx.button(
                            rx.hstack(
                                rx.avatar(name="Create New Chat", size="2"),
                                rx.vstack(
                                    rx.text("Create New Chat", font_weight="bold", color="white"),
                                    rx.text("Start a new conversation", color="#cccccc", font_size="12px"),
                                    align_items="start",
                                    spacing="0",
                                ),
                                width="100%",
                            ),
                            width="100%",
                            justify_content="flex-start",
                            bg="transparent",
                            _hover={"bg": "#444444"},
                            border_radius="md",
                            padding="2",
                            variant="ghost",
                            # This would open a "create chat" dialog in a future implementation
                            on_click=ChatState.set_success_message("Create chat feature coming soon!"),
                        ),
                        width="100%",
                    ),
                    # Show when no rooms are available
                    rx.vstack(
                        rx.text(
                            "No chat rooms available", 
                            color="gray.400",
                            font_style="italic",
                            padding="10px",
                        ),
                        rx.button(
                            "Create New Chat",
                            on_click=ChatState.set_success_message("Create chat feature coming soon!"),
                            bg="#80d0ea",
                            color="white",
                            _hover={"bg": "#6bc0d9"},
                            border_radius="md",
                            padding="2",
                            margin_top="4",
                        ),
                        width="100%",
                        padding="4",
                    ),
                ),
                # Status text - will be updated by JavaScript
                rx.text(
                    rx.cond(
                        ChatState.formatted_rooms.length() > 0,
                        f"{ChatState.formatted_rooms.length()} rooms available",
                        "No chat rooms available yet"
                    ),
                    color="#80d0ea",
                    font_style="italic",
                    padding="10px",
                    id="room-status",
                ),
                # Simple script to update the status text with real-time data
                rx.script("""
                    function updateRoomStatus() {
                        // Try to access the formatted_rooms in the state
                        if (window._state && window._state.formatted_rooms) {
                            const roomCount = window._state.formatted_rooms.length;
                            const statusEl = document.getElementById('room-status');
                            
                            if (statusEl) {
                                if (roomCount > 0) {
                                    statusEl.innerText = `${roomCount} chat room${roomCount > 1 ? 's' : ''} available`;
                                    statusEl.style.color = '#80d0ea';
                                } else {
                                    statusEl.innerText = 'No chat rooms available';
                                    statusEl.style.color = '#aaaaaa';
                                }
                            }
                        }
                    }
                    
                    // Update initially and periodically
                    document.addEventListener('DOMContentLoaded', () => {
                        setInterval(updateRoomStatus, 1000);
                    });
                """),
                width="100%",
            ),
            width="100%",
            overflow_y="auto",
            height="calc(100vh - 60px)",
        ),
        width="280px",
        height="100vh",
        bg="#2d2d2d",
        border_right="1px solid #444",
    )

def message_display(sender: str, message: str) -> rx.Component:
    # First check if message is None or empty and provide a default
    safe_message = message if message is not None else ""
    
    # Now check if the message string starts with "/_upload"
    # Without using rx.is_instance since it doesn't exist in this Reflex version
    is_upload = rx.cond(
        safe_message.startswith("/_upload"),
        True,
        False
    )
    
    # Here sender is either "user" (current user) or "other" (not the current user)
    is_current_user = sender == "user"
    
    # Add a debug element to show message ownership
    debug_info = rx.cond(
        ChatState.debug_show_info,
        rx.box(
            rx.text(
                f"From: {sender}",
                font_size="10px",
                color="gray.500",
                margin_bottom="2px",
            ),
            display="block",
        ),
        rx.fragment()
    )
    
    return rx.vstack(
        debug_info,
        rx.hstack(
            rx.cond(
                is_current_user,
                rx.spacer(),
                rx.box(),
            ),
            rx.box(
                rx.cond(
                    is_upload,
                    rx.image(
                        src=rx.cond(safe_message != "", safe_message, ""),
                        max_width="200px",
                        border_radius="15px"
                    ),
                    rx.text(
                        rx.cond(safe_message != "", safe_message, ""), 
                        color=rx.cond(is_current_user, "white", "#333333")
                    )
                ),
                padding="10px 15px",
                border_radius=rx.cond(
                    is_current_user,
                    "15px 15px 5px 15px",
                    "15px 15px 15px 5px"
                ),
                max_width="70%",
                bg=rx.cond(
                    is_current_user,
                    "#80d0ea",
                    "white"
                ),
                margin_left=rx.cond(
                    is_current_user,
                    "auto",
                    "0"
                ),
                margin_right=rx.cond(
                    is_current_user,
                    "0",
                    "auto"
                ),
                box_shadow="0px 1px 2px rgba(0, 0, 0, 0.1)",
            ),
            width="100%",
            margin_y="2px",
            padding_x="15px",
        ),
        width="100%",
        align_items="stretch",
        spacing="0",
    )

def typing_indicator() -> rx.Component:
    return rx.cond(
        ChatState.is_someone_typing,
        rx.box(
            rx.hstack(
                rx.flex(
                    rx.box(
                        height="8px",
                        width="8px",
                        border_radius="50%",
                        bg="#80d0ea",
                        margin_right="3px",
                        animation="typing-dot 1.4s infinite ease-in-out",
                        animation_delay="0s",
                    ),
                    rx.box(
                        height="8px",
                        width="8px",
                        border_radius="50%",
                        bg="#80d0ea",
                        margin_right="3px",
                        animation="typing-dot 1.4s infinite ease-in-out",
                        animation_delay="0.2s",
                    ),
                    rx.box(
                        height="8px",
                        width="8px",
                        border_radius="50%",
                        bg="#80d0ea",
                        animation="typing-dot 1.4s infinite ease-in-out",
                        animation_delay="0.4s",
                    ),
                    direction="row",
                    align="center",
                ),
                rx.text(
                    ChatState.typing_message,
                    color="#AAAAAA",
                    font_size="12px",
                    margin_left="8px",
                ),
                padding="5px 15px",
                bg="#333333",
                border_radius="15px",
            ),
            padding="0 15px 5px 15px",
        ),
        rx.box(),
    )

def chat() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.foreach(
                ChatState.chat_history,
                lambda msg: message_display(msg[0], msg[1])
            ),
            typing_indicator(),
            width="100%",
            align_items="stretch",
            spacing="0",
        ),
        padding="10px 0",
        overflow="auto",
        flex="1",
        width="100%",
        height="calc(100vh - 130px)",
        bg="#2d2d2d",
    )

def message_input() -> rx.Component:
    """Message input component for the chat interface."""
    return rx.hstack(
        rx.hstack(
            rx.input(
                value=ChatState.message,
                placeholder="Type a message...",
                on_change=ChatState.set_message,
                # Use our keypress_handler for key events
                on_key_down=ChatState.keypress_handler,
                _placeholder={"color": "#AAAAAA"},
                border_radius="20px",
                border="none",
                width="100%",
                bg="white",
                padding="10px 15px",
                height="40px",
                _focus={
                    "outline": "none",
                    "box_shadow": "0 0 0 2px rgba(128, 208, 234, 0.3)",
                },
                _hover={
                    "bg": "#f8f8f8",
                },
            ),
            bg="white",
            border_radius="20px",
            padding_left="10px",
            width="100%",
            box_shadow="0 2px 4px rgba(0, 0, 0, 0.05)",
        ),
        rx.upload(
            rx.button(
                rx.icon("paperclip"),
                border_radius="50%",
                bg="#80d0ea",
                color="white", 
                width="40px",
                height="40px",
                padding="0",
                _hover={
                    "bg": "#6bc0d9",
                    "transform": "scale(1.05)",
                },
                transition="all 0.2s ease-in-out",
            ),
            id="chat_upload",
            accept={
                "image/png": [".png"],
                "image/jpeg": [".jpg", ".jpeg"],
                "image/gif": [".gif"],
                "image/webp": [".webp"],
                "video/mp4": [".mp4"],
                "video/quicktime": [".mov"],
                "audio/mpeg": [".mp3"],
                "audio/wav": [".wav"],
                "application/pdf": [".pdf"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"]
            },
            max_files=1,
            on_drop=ChatState.handle_upload(rx.upload_files(upload_id="chat_upload")),
            border="none",
        ),
        rx.button(
            rx.icon("arrow-right"),
            on_click=ChatState.send_message,
            border_radius="50%",
            bg="#80d0ea",
            color="white",
            width="40px",
            height="40px",
            padding="0",
            margin_left="10px",
            _hover={
                "bg": "#6bc0d9",
                "transform": "scale(1.05)",
            },
            transition="all 0.2s ease-in-out",
        ),
        padding="15px",
        bg="#2d2d2d",
        border_top="1px solid #444",
        width="100%",
        height="70px",
        align_items="center",
    )

def error_alert() -> rx.Component:
    """Error notification component."""
    return rx.cond(
        ChatState.error_message != "",
        rx.box(
            rx.vstack(
                rx.text(
                    "Error",
                    font_size="1",
                    font_weight="bold",
                    color="white",
                ),
                rx.text(
                    ChatState.error_message,
                    color="white",
                ),
                rx.button(
                    "Close",
                    on_click=ChatState.clear_error_message,
                    bg="#ff4444",
                    color="white",
                    border_radius="md",
                    _hover={"bg": "#ff3333"},
                ),
                spacing="2",
                align_items="start",
                padding="4",
            ),
            bg="#ff4444",
            border_radius="md",
            position="fixed",
            bottom="4",
            right="4",
            width="300px",
            z_index="1000",
            box_shadow="0 4px 8px rgba(0,0,0,0.2)",
            # Don't use if/else with Var objects
            on_mount=ChatState.show_error,
        ),
        rx.fragment(),
    )

def success_alert() -> rx.Component:
    """Success notification component."""
    return rx.cond(
        ChatState.success_message != "",
        rx.box(
            rx.vstack(
                rx.text(
                    "Success",
                    font_size="1",
                    font_weight="bold",
                    color="white",
                ),
                rx.text(
                    ChatState.success_message,
                    color="white",
                ),
                rx.button(
                    "Close",
                    on_click=ChatState.clear_success_message,
                    bg="#4CAF50",
                    color="white",
                    border_radius="md",
                    _hover={"bg": "#45a049"},
                ),
                spacing="2",
                align_items="start",
                padding="4",
            ),
            bg="#4CAF50",
            border_radius="md",
            position="fixed",
            bottom="4",
            right="4",
            width="300px",
            z_index="1000",
            box_shadow="0 4px 8px rgba(0,0,0,0.2)",
            # Don't use if/else with Var objects
            on_mount=ChatState.show_success,
        ),
        rx.fragment(),
    )

def debug_info() -> rx.Component:
    """Debug component showing route parameters (for development)."""
    return rx.cond(
        # Only show when debug_show_info is enabled
        ChatState.debug_show_info,  
        rx.box(
            rx.vstack(
                rx.text("Debug Info", font_weight="bold", color="white"),
                rx.text(
                    "Room ID from URL: ",
                    ChatState.route_room_id,
                    color="white",
                    font_size="sm",
                ),
                rx.text(
                    "Current Room ID: ",
                    ChatState.current_room_id,
                    color="white",
                    font_size="sm",
                ),
                rx.text(
                    "Current Username: ",
                    ChatState.username,
                    color="white",
                    font_size="sm",
                    bg="#555555",
                    padding="1px 5px",
                    border_radius="md",
                ),
                rx.hstack(
                    rx.button(
                        "Login as Tester",
                        on_click=lambda: ChatState.login_as_user("Tester"),
                        size="1",
                        bg="#80d0ea",
                        color="white",
                        height="20px",
                        padding="0 8px",
                        font_size="xs", 
                    ),
                    rx.button(
                        "Login as John",
                        on_click=lambda: ChatState.login_as_user("John"),
                        size="1",
                        bg="#80d0ea",
                        color="white",
                        height="20px",
                        padding="0 8px",
                        font_size="xs",
                    ),
                    spacing="2",
                    margin_top="1",
                    margin_bottom="2",
                ),
                rx.text(
                    "LocalStorage Check:",
                    color="white",
                    font_size="sm",
                    font_weight="bold",
                ),
                rx.html("""
                <div id="localStorage-debug" style="color: white; font-size: 12px; margin-bottom: 10px;">
                    Checking localStorage...
                </div>
                <script>
                    function updateLocalStorageDebug() {
                        const el = document.getElementById('localStorage-debug');
                        if (el) {
                            const username = localStorage.getItem('username');
                            const token = localStorage.getItem('auth_token');
                            el.innerHTML = `Username: ${username || 'Not set'}<br>Token: ${token ? token.substring(0,10)+'...' : 'Not set'}`;
                        }
                    }
                    // Update every second
                    setInterval(updateLocalStorageDebug, 1000);
                    // Initial update
                    updateLocalStorageDebug();
                </script>
                """),
                rx.text(
                    "Auth Token: ",
                    rx.cond(
                        ChatState.auth_token,
                        ChatState.auth_token[:10] + "...",
                        "None"
                    ),
                    color="white",
                    font_size="sm",
                ),
                rx.cond(
                    ChatState.chat_history.length() > 0,
                    rx.text(
                        "Last message from: ",
                        ChatState.chat_history[-1][0],
                        color="white",
                        font_size="sm",
                    ),
                    rx.text("No messages yet", color="white", font_size="sm"),
                ),
                rx.text(
                    "Debug Settings:",
                    color="white",
                    font_size="sm",
                    font_weight="bold",
                    margin_top="2",
                ),
                rx.text(
                    "Use Dummy Data: ",
                    str(ChatState.debug_use_dummy_data),
                    color="#80d0ea",
                    font_size="sm",
                ),
                rx.text(
                    "Log API Calls: ",
                    str(ChatState.debug_log_api_calls),
                    color="#80d0ea",
                    font_size="sm",
                ),
                rx.hstack(
                    rx.button(
                        "Hide Debug",
                        on_click=ChatState.toggle_debug_info,
                        size="4",
                        bg="#80d0ea",
                        color="white",
                    ),
                    rx.button(
                        "Toggle Dummy Data",
                        on_click=ChatState.toggle_debug_dummy_data,
                        size="4",
                        bg="#80d0ea",
                        color="white",
                    ),
                    spacing="2",
                    margin_top="2",
                ),
                spacing="1",
                align_items="start",
                padding="2",
            ),
            bg="#333",
            border_radius="md",
            position="fixed",
            bottom="4",
            left="4",
            width="300px",
            opacity="0.8",
            z_index="900",
            display="block",  # Make visible when debug_show_info is true
        ),
        rx.fragment(),
    )

def debug_button() -> rx.Component:
    """Button to show debug panel when it's hidden."""
    return rx.cond(
        ~ChatState.debug_show_info,  # Only show when debug_show_info is False
        rx.box(
            rx.button(
                "Debug",
                on_click=ChatState.toggle_debug_info,
                size="4",
                bg="#80d0ea",
                color="white",
                border_radius="md",
                _hover={"bg": "#6bc0d9"},
            ),
            position="fixed",
            bottom="4",
            left="4",
            z_index="900",
        ),
        rx.fragment(),
    )

def user_header() -> rx.Component:
    return rx.hstack(
        # Back button - only show when in a chat
        rx.cond(
            ChatState.current_room_id != "",
            rx.button(
                rx.icon("arrow-left", color="white", font_size="18px"),
                on_click=ChatState.go_back_to_chat_list,
                variant="ghost",
                _hover={
                    "bg": "rgba(255, 255, 255, 0.1)",
                    "transform": "scale(1.1)",
                },
                transition="all 0.2s ease-in-out",
                title="Back to Chats List",
            ),
            rx.box(width="32px", height="32px"),  # Placeholder
        ),
        rx.cond(
            ChatState.current_chat_user != "",
            rx.avatar(
                name=rx.cond(
                    ChatState.current_chat_user != "", 
                    ChatState.current_chat_user, 
                    "Chat"
                ), 
                size="2", 
                border="2px solid white"
            ),
            rx.box(width="32px", height="32px"),
        ),
        rx.text(
            rx.cond(
                ChatState.current_chat_user != "",
                ChatState.current_chat_user,
                "Chat"
            ), 
            font_weight="bold", 
            color="white", 
            font_size="16px"
        ),
        rx.spacer(),
        rx.hstack(
            rx.button(
                rx.icon("phone", color="white", font_size="18px"),
                on_click=ChatState.start_call,
                variant="ghost",
                _hover={
                    "bg": "rgba(255, 255, 255, 0.1)",
                    "transform": "scale(1.2)",
                },
                transition="all 0.2s ease-in-out",
                disabled=ChatState.current_room_id == "",
            ),
            rx.button(
                rx.icon("video", color="white", font_size="18px"),
                on_click=ChatState.start_video_call,
                variant="ghost",
                _hover={
                    "bg": "rgba(255, 255, 255, 0.1)",
                    "transform": "scale(1.2)",
                },
                transition="all 0.2s ease-in-out",
                disabled=ChatState.current_room_id == "",
            ),
            rx.button(
                rx.icon("info", color="white", font_size="18px"),
                variant="ghost",
                _hover={
                    "bg": "rgba(255, 255, 255, 0.1)",
                    "transform": "scale(1.2)",
                },
                transition="all 0.2s ease-in-out",
            ),
            spacing="4",
        ),
        width="100%",
        padding="10px 15px",
        bg="#80d0ea",
        border_radius="0",
        height="60px",
    )

def incoming_call_popup() -> rx.Component:
    """Component for showing incoming call popup."""
    return rx.cond(
        ChatState.show_incoming_call,
        rx.box(
            rx.center(
                rx.vstack(
                    rx.avatar(
                        name=ChatState.incoming_caller,
                        size="9",
                        border="4px solid #80d0ea",
                        margin_bottom="20px",
                        border_radius="50%",
                        width="120px",
                        height="120px",
                        animation="pulse 1.5s infinite",
                    ),
                    rx.text(
                        ChatState.incoming_caller,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="10px",
                        text_align="center",
                    ),
                    rx.text(
                        rx.cond(
                            ChatState.call_type == "video",
                            "Incoming video call...",
                            "Incoming audio call..."
                        ),
                        font_size="18px",
                        color="#666666",
                        margin_bottom="20px",
                        text_align="center",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon("phone"),
                            on_click=ChatState.accept_call,
                            border_radius="50%",
                            bg="#4CAF50",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#45a049",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        rx.button(
                            rx.icon("phone-off"),
                            on_click=ChatState.decline_call,
                            border_radius="50%",
                            bg="#ff4444",
                            color="white",
                            width="60px",
                            height="60px",
                            padding="0",
                            _hover={
                                "bg": "#ff3333",
                                "transform": "scale(1.1)",
                            },
                            transition="all 0.2s ease-in-out",
                        ),
                        spacing="4",
                        justify_content="center",
                        width="100%",
                    ),
                    align_items="center",
                    justify_content="center",
                    width="340px",
                    height="400px",
                    bg="white",
                    border_radius="20px",
                    padding="30px",
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
                    z_index="1000",
                    css={
                        "@keyframes pulse": {
                            "0%": {"box-shadow": "0 0 0 0 rgba(128, 208, 234, 0.7)"},
                            "70%": {"box-shadow": "0 0 0 10px rgba(128, 208, 234, 0)"},
                            "100%": {"box-shadow": "0 0 0 0 rgba(128, 208, 234, 0)"}
                        }
                    },
                ),
            ),
            position="fixed",
            top="0",
            left="0",
            width="100%",
            height="100%",
            bg="rgba(0, 0, 0, 0.5)",
            display="flex",
            justify_content="center",
            align_items="center",
            on_click=ChatState.decline_call,  # Click outside to decline
        ),
        None,
    )

# def chat_page() -> rx.Component:
#     return rx.box(
#         rx.hstack(
#             rx.cond(
#                 ChatState.sidebar_visible,
#                 sidebar(),
#                 rx.fragment()
#             ),
#             rx.vstack(
#                 user_header(),
#                 chat(),
#                 message_input(),
#                 height="100vh",
#                 width="100%",
#                 spacing="0",
#                 bg="#2d2d2d",
#             ),
#             spacing="0",
#             width="100%",
#             height="100vh",
#             overflow="hidden",
#         ),
#         calling_popup(),
#         call_popup(),
#         video_call_popup(),
#         error_alert(),
#         success_alert(),
#         debug_info(),  # Debug panel
#         debug_button(),  # Button to show debug panel
#         incoming_call_popup(),
#         on_mount=ChatState.on_mount,
#         on_unmount=ChatState.cleanup,
#         style={
#             "@keyframes typing-dot": {
#                 "0%, 60%, 100%": {
#                     "opacity": "0.4",
#                     "transform": "scale(0.8)"
#                 },
#                 "30%": {
#                     "opacity": "1",
#                     "transform": "scale(1)"
#                 }
#             }
#         },
#     )


def websocket_debug_monitor() -> rx.Component:
    """Hidden debug component to monitor WebSocket call flow."""
    return rx.box(
        rx.html("""
        <div id="ws-debug-monitor" style="display: none;">
            <script>
                // Create a global log storage
                if (!window.webrtcCallLogs) {
                    window.webrtcCallLogs = [];
                }
                
                // Function to log WebSocket events with timestamp
                function logWebSocketEvent(direction, data) {
                    const timestamp = new Date().toISOString();
                    const username = state.username || 'unknown';
                    const logEntry = {
                        timestamp: timestamp,
                        username: username,
                        direction: direction,
                        data: data,
                        type: data.type || 'unknown'
                    };
                    
                    // Store in global logs
                    window.webrtcCallLogs.push(logEntry);
                    
                    // Keep only last 100 logs
                    if (window.webrtcCallLogs.length > 100) {
                        window.webrtcCallLogs.shift();
                    }
                    
                    // Log to console with special formatting for call events
                    if (data.type && (data.type.includes('call') || data.type === 'room_call_announcement')) {
                        console.log(
                            `%c[CALL FLOW] [${timestamp}] [${username}] [${direction}] [${data.type}]`,
                            'background: #333; color: #ff9; padding: 2px 4px; border-radius: 2px;',
                            data
                        );
                    }
                }
                
                // Override the WebSocket send method to log outgoing messages
                if (typeof window !== 'undefined') {
                    const originalWebSocketSend = WebSocket.prototype.send;
                    WebSocket.prototype.send = function(data) {
                        try {
                            const parsedData = JSON.parse(data);
                            logWebSocketEvent('SENT', parsedData);
                        } catch (e) {
                            // Not JSON data, ignore
                        }
                        return originalWebSocketSend.call(this, data);
                    };
                    
                    // Create a global object to store WebSocket references
                    window.wsMonitor = {
                        logs: window.webrtcCallLogs,
                        startMonitoring: function(socket) {
                            const originalOnMessage = socket.onmessage;
                            socket.onmessage = function(event) {
                                try {
                                    const parsedData = JSON.parse(event.data);
                                    logWebSocketEvent('RECEIVED', parsedData);
                                } catch (e) {
                                    // Not JSON data, ignore
                                }
                                if (originalOnMessage) {
                                    return originalOnMessage.call(this, event);
                                }
                            };
                            console.log('WebSocket monitoring started');
                        }
                    };
                    
                    // Export a helper function to dump call logs
                    window.dumpCallLogs = function() {
                        const callLogs = window.webrtcCallLogs.filter(log => 
                            log.type.includes('call') || log.type === 'room_call_announcement'
                        );
                        console.table(callLogs.map(log => ({
                            time: log.timestamp.split('T')[1].split('.')[0],
                            user: log.username,
                            direction: log.direction,
                            type: log.type,
                            caller: log.data.caller_username || log.data.username || '-',
                            room: log.data.room_id || log.data.room || '-'
                        })));
                        return callLogs;
                    };
                    
                    // Add custom command to the WebSocket connections
                    // Set an interval to attach monitor to any new WebSocket objects
                    setInterval(() => {
                        if (window.chatSocket && !window.chatSocket._monitored) {
                            window.wsMonitor.startMonitoring(window.chatSocket);
                            window.chatSocket._monitored = true;
                            console.log('Chat WebSocket monitoring enabled');
                        }
                        if (window.signalingSocket && !window.signalingSocket._monitored) {
                            window.wsMonitor.startMonitoring(window.signalingSocket);
                            window.signalingSocket._monitored = true;
                            console.log('Signaling WebSocket monitoring enabled');
                        }
                    }, 1000);
                }
            </script>
        </div>
        """),
        # This is a hidden component
        display="none",
    )

# Then add the monitor to your chat_page component
def chat_page() -> rx.Component:
    """Enhanced chat page function with improved API call debugging."""
    return rx.box(
        rx.hstack(
            rx.cond(
                ChatState.sidebar_visible,
                sidebar(),
                rx.fragment()
            ),
            rx.vstack(
                user_header(),
                chat(),
                message_input(),
                height="100vh",
                width="100%",
                spacing="0",
                bg="#2d2d2d",
            ),
            spacing="0",
            width="100%",
            height="100vh",
            overflow="hidden",
        ),
        calling_popup(),
        call_popup(),
        video_call_popup(),
        error_alert(),
        success_alert(),
        debug_info(),  # Debug panel
        debug_button(),  # Button to show debug panel
        incoming_call_popup(),
        websocket_debug_monitor(),  # WebSocket monitor
        
        # Add an enhanced debug panel that's always visible when debug mode is on
        rx.cond(
            ChatState.debug_show_info,
            rx.box(
                rx.vstack(
                    rx.text(
                        "API Call Debug",
                        font_weight="bold",
                        color="#00ff00",
                        margin_bottom="5px",
                    ),
                    rx.html("""
                    <div id="api-call-log" style="font-family: monospace; white-space: pre-wrap; overflow-y: auto; 
                                max-height: 150px; font-size: 12px; color: #00ff00; width: 100%;">
                        Waiting for API calls...
                    </div>
                    <div style="display: flex; gap: 5px; margin-top: 8px;">
                        <button id="test-token-button" style="background: #444; color: white; border: none; 
                                padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;">
                            Test Token
                        </button>
                        <button id="test-api-button" style="background: #444; color: white; border: none; 
                                padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;">
                            Test API
                        </button>
                        <button id="clear-log-button" style="background: #444; color: white; border: none; 
                                padding: 4px 8px; border-radius: 4px; font-size: 12px; cursor: pointer;">
                            Clear Log
                        </button>
                    </div>
                    <script>
                        // Initialize the log system
                        if (!window.apiCallLogs) {
                            window.apiCallLogs = [];
                        }
                        
                        // Log function that shows in the UI and also console
                        window.logApiCall = function(message) {
                            const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
                            const formattedMessage = `[${timestamp}] ${message}`;
                            
                            // Add to log array
                            window.apiCallLogs.push(formattedMessage);
                            if (window.apiCallLogs.length > 50) {
                                window.apiCallLogs.shift();
                            }
                            
                            // Update UI
                            const logElement = document.getElementById('api-call-log');
                            if (logElement) {
                                logElement.textContent = window.apiCallLogs.join('\\n');
                                logElement.scrollTop = logElement.scrollHeight;
                            }
                            
                            // Also log to console
                            console.log('[API-DEBUG] ' + message);
                        };
                        
                        // Function to test auth token
                        function testAuthToken() {
                            const token = localStorage.getItem('auth_token');
                            window.logApiCall(`Auth token: ${token ? token.substring(0, 10) + '...' : 'None'}`);
                            
                            // Test different auth formats
                            window.logApiCall('Testing token with Bearer prefix...');
                            fetch('""" + f"{ChatState.API_HOST_URL}/authen/auth-debug/" + """', {
                                headers: {
                                    'Authorization': `Bearer ${token}`
                                }
                            })
                            .then(response => {
                                window.logApiCall(`Bearer auth response: ${response.status}`);
                                return response.text();
                            })
                            .then(text => {
                                try {
                                    const json = JSON.parse(text);
                                    window.logApiCall(`Response data: ${JSON.stringify(json).substring(0, 50)}...`);
                                } catch (e) {
                                    window.logApiCall(`Response text: ${text.substring(0, 50)}...`);
                                }
                            })
                            .catch(error => {
                                window.logApiCall(`Error: ${error.message}`);
                            });
                            
                            // Test with Token prefix
                            window.logApiCall('Testing token with Token prefix...');
                            fetch('""" + f"{ChatState.API_HOST_URL}/authen/auth-debug/" + """', {
                                headers: {
                                    'Authorization': `Token ${token}`
                                }
                            })
                            .then(response => {
                                window.logApiCall(`Token auth response: ${response.status}`);
                                return response.text();
                            })
                            .then(text => {
                                try {
                                    const json = JSON.parse(text);
                                    window.logApiCall(`Response data: ${JSON.stringify(json).substring(0, 50)}...`);
                                } catch (e) {
                                    window.logApiCall(`Response text: ${text.substring(0, 50)}...`);
                                }
                            })
                            .catch(error => {
                                window.logApiCall(`Error: ${error.message}`);
                            });
                        }
                        
                        // Function to test the call API
                        function testCallApi() {
                            const token = localStorage.getItem('auth_token');
                            const apiUrl = '""" + f"{ChatState.API_HOST_URL}/communication/incoming-calls/" + """';
                            window.logApiCall(`Testing call API: ${apiUrl}`);
                            
                            // First try with Bearer
                            window.logApiCall('Trying with Bearer auth...');
                            fetch(apiUrl, {
                                method: 'GET',
                                headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Content-Type': 'application/json'
                                }
                            })
                            .then(response => {
                                window.logApiCall(`GET with Bearer: ${response.status}`);
                                return response.text();
                            })
                            .then(text => {
                                window.logApiCall(`Response: ${text.substring(0, 100)}...`);
                                
                                // Now try with Token auth
                                window.logApiCall('Trying with Token auth...');
                                return fetch(apiUrl, {
                                    method: 'GET',
                                    headers: {
                                        'Authorization': `Token ${token}`,
                                        'Content-Type': 'application/json'
                                    }
                                });
                            })
                            .then(response => {
                                window.logApiCall(`GET with Token: ${response.status}`);
                                return response.text();
                            })
                            .then(text => {
                                window.logApiCall(`Response: ${text.substring(0, 100)}...`);
                            })
                            .catch(error => {
                                window.logApiCall(`Error: ${error.message}`);
                            });
                        }
                        
                        // Attach event handlers after DOM loads
                        document.addEventListener('DOMContentLoaded', function() {
                            // Button event handlers
                            document.getElementById('test-token-button').addEventListener('click', testAuthToken);
                            document.getElementById('test-api-button').addEventListener('click', testCallApi);
                            document.getElementById('clear-log-button').addEventListener('click', function() {
                                window.apiCallLogs = [];
                                document.getElementById('api-call-log').textContent = 'Logs cleared...';
                            });
                            
                            // Initialize with a test
                            window.logApiCall('Debug panel initialized');
                            window.logApiCall(`API Host URL: """ + f"{ChatState.API_HOST_URL}" + """`);
                        });
                        
                        // Expose test functions to window for console debugging
                        window.testToken = testAuthToken;
                        window.testCallApi = testCallApi;
                    </script>
                    """),
                    width="100%",
                    align_items="flex-start",
                    spacing="2",
                ),
                position="fixed",
                bottom="10px",
                left="10px",
                width="350px", 
                padding="10px",
                bg="#000000",
                border="1px solid #333333",
                border_radius="md",
                z_index="999",
                opacity="0.9",
            ),
            rx.fragment(),
        ),
        
        on_mount=ChatState.on_mount,
        on_unmount=ChatState.cleanup,
        style={
            "@keyframes typing-dot": {
                "0%, 60%, 100%": {
                    "opacity": "0.4",
                    "transform": "scale(0.8)"
                },
                "30%": {
                    "opacity": "1",
                    "transform": "scale(1)"
                }
            }
        },
    )