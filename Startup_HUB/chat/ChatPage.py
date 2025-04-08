import reflex as rx
import json
import asyncio
import httpx
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
    debug_use_dummy_data: bool = True   # Use dummy data instead of API calls where needed
    debug_log_api_calls: bool = True    # Log API calls and responses
    
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
        """Initialize when the component mounts."""
        print("\n=== ChatPage Mounted ===")
        
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
        print(f"\n===== Opening room: {room_id}, name: {room_name} =====")
        
        if not room_id:
            print("No room ID provided to open_room method")
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot open room")
            self.error_message = "Not authenticated. Please log in."
            return

        # Force room_id to be a string
        room_id = str(room_id)
        print(f"Room ID (forced to string): {room_id}")
        
        # 1. Set the room details
        self.current_room_id = room_id
        
        # 2. Set initial room name if provided
        if room_name:
            # Set it initially, but we'll confirm it when loading messages
            self.current_chat_user = room_name
            print(f"Setting initial room name: {room_name}")
        else:
            # Clear it so load_messages will load the correct name from the server
            self.current_chat_user = ""
                
        print(f"Set current_room_id to {self.current_room_id}")
        
        # Check if we need to reload rooms before loading messages
        if not self.rooms:
            print("No rooms loaded yet, loading rooms first")
            await self.load_rooms()
            
        # 3. Load messages for this room (this will also fetch the correct room name)
        try:
            await self.load_messages()
            
            # 4. Connect to WebSocket for this room
            await self.on_room_open()
            
            # 5. Update the URL to reflect the current room
            # Only update URL if we're not already on this room's URL
            if hasattr(self, "router"):
                current_params = getattr(self.router.page, "params", {})
                current_room_id = current_params.get("room_id", "")
                
                if current_room_id != room_id:
                    print(f"Updating URL to /chat/room/{room_id}")
                    return rx.redirect(f"/chat/room/{room_id}")
        except Exception as e:
            print(f"Error loading room: {str(e)}")
            self.error_message = f"Failed to load room: {str(e)}"

    @rx.event
    async def connect_chat_websocket(self):
        """Connect to the chat WebSocket for the current room."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            self.error_message = "Not authenticated"
            return
            
        room_id_str = str(self.current_room_id)
        
        # Get WebSocket URL
        ws_protocol = "wss://" if "https:" in self.API_BASE_URL else "ws://"
        ws_base = self.API_BASE_URL.replace("https://", "").replace("http://", "")
        ws_url = f"{ws_protocol}{ws_base}/ws/chat/{room_id_str}/?token={self.auth_token}"
        
        # Connect to the WebSocket
        rx.call_script(f"""
            // Close any existing connection
            if (window.chatSocket) {{
                window.chatSocket.close();
                window.chatSocket = null;
            }}
            
            // Create new WebSocket connection
            window.chatSocket = new WebSocket("{ws_url}");
            
            window.chatSocket.onopen = function(event) {{
                console.log('[WebRTC Debug] Chat WebSocket connected to room {room_id_str}');
                state.is_connected = true;
                
                // Send join message
                window.chatSocket.send(JSON.stringify({{
                    type: 'join',
                    room_id: '{room_id_str}'
                }}));
            }};
            
            window.chatSocket.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                console.log('[WebRTC Debug] Chat WebSocket message received:', data);
                
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
                    case 'call_notification':
                    case 'incoming_call':
                        // Handle direct incoming call notification
                        console.log('[WebRTC Debug] Direct call notification received:', data);
                        
                        // Don't handle calls initiated by this user
                        if (data.caller_username === state.username) {{
                            console.log('[WebRTC Debug] Ignoring our own call notification');
                            break;
                        }}
                        
                        if (window.callHandler && typeof window.callHandler.handleIncomingCall === 'function') {{
                            console.log('[WebRTC Debug] Using external call handler for direct call');
                            try {{
                                // Set the type for the handler to know it's a direct call
                                data.type = 'incoming_call';
                                window.callHandler.handleIncomingCall(data, state);
                            }} catch (err) {{
                                console.error('[WebRTC Debug] Error in external call handler:', err);
                                handleIncomingCallFallback(data);
                            }}
                        }} else {{
                            console.log('[WebRTC Debug] External call handler not available, using fallback');
                            handleIncomingCallFallback(data);
                        }}
                        break;
                    case 'room_call_announcement':
                        // Handle room-wide call announcement
                        console.log('[WebRTC Debug] Room-wide call announcement received:', data);
                        
                        // Don't handle calls initiated by this user
                        if (data.caller_username === state.username) {{
                            console.log('[WebRTC Debug] Ignoring our own room call announcement');
                            break;
                        }}
                        
                        if (window.callHandler && typeof window.callHandler.handleIncomingCall === 'function') {{
                            console.log('[WebRTC Debug] Notifying of room-wide call');
                            try {{
                                window.callHandler.handleIncomingCall(data, state);
                            }} catch (err) {{
                                console.error('[WebRTC Debug] Error handling room call announcement:', err);
                            }}
                        }}
                        break;
                    case 'join_call_notification':
                        // Someone joined the call
                        console.log('[WebRTC Debug] User joined call:', data.username);
                        
                        // Show a toast notification that someone joined
                        rx.call_script(`
                            const joinToast = document.createElement('div');
                            joinToast.style.cssText = 'position:fixed;bottom:20px;left:20px;background:#333;color:white;padding:12px;border-radius:4px;z-index:9999;';
                            joinToast.innerHTML = '<strong>${data.username}</strong> joined the call';
                            document.body.appendChild(joinToast);
                            
                            // Auto-remove after 3 seconds
                            setTimeout(() => {{
                                joinToast.style.opacity = '0';
                                joinToast.style.transition = 'opacity 0.5s';
                                setTimeout(() => document.body.removeChild(joinToast), 500);
                            }}, 3000);
                        `);
                        break;
                    case 'call_response':
                        // Handle call response (accept/decline)
                        handleCallResponse(data);
                        break;
                    case 'end_call':
                        // Handle call end
                        console.log('[WebRTC Debug] Received end_call notification:', data);
                        
                        // Clean up call resources
                        if (window.callHandler && typeof window.callHandler.cleanupCall === 'function') {{
                            console.log('[WebRTC Debug] Using external cleanup handler');
                            window.callHandler.cleanupCall();
                            
                            // Also remove from active calls
                            if (data.room_id && typeof window.callHandler.removeActiveCall === 'function') {{
                                window.callHandler.removeActiveCall(data.room_id);
                            }}
                        }} else {{
                            console.log('[WebRTC Debug] Using fallback cleanup');
                            // Fallback cleanup
                            if (window.ringtoneElement) {{
                                window.ringtoneElement.pause();
                                window.ringtoneElement.currentTime = 0;
                            }}
                            if (window.titleFlashInterval) {{
                                clearInterval(window.titleFlashInterval);
                                document.title = 'Chat';
                            }}
                        }}
                        
                        // Update UI state
                        setTimeout(() => {{
                            state.show_incoming_call = false;
                            state.show_calling_popup = false;
                            state.show_call_popup = false;
                            state.show_video_popup = false;
                            state.is_call_connected = false;
                            state.active_room_call = {{}}; // Clear active room call data
                            state._update();
                        }}, 0);
                        break;
                    case 'error':
                        console.error('[WebRTC Debug] Chat WebSocket error:', data.message);
                        state.error_message = data.message;
                        break;
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
            
            // Function to handle new message
            function handleNewMessage(data) {{
                const message = data.message;
                if (!message) return;
                
                // Check if the message is from current user
                const isCurrentUser = message.sender.username === state.username;
                
                // Add message to chat history
                console.log(`[WebRTC Debug] Adding message from ${{message.sender.username}}`);
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
            
            // Function to handle call response
            function handleCallResponse(data) {{
                console.log('[WebRTC Debug] Call response received:', data);
                
                // Get response details
                const response = data.response;
                
                // Update state immediately
                if (response === 'accept') {{
                    // Call was accepted, continue with establishing connection
                    console.log('[WebRTC Debug] Call accepted');
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
                    console.log('[WebRTC Debug] Call declined');
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
            
            // Fallback function for handling incoming calls when the external script isn't loaded
            function handleIncomingCallFallback(data) {{
                console.log('[WebRTC Debug] Using fallback incoming call handler');
                
                const caller = data.caller_username;
                const callType = data.call_type || 'audio';
                const invitationId = data.invitation_id || '';
                
                // Log the call details and state before updating
                console.log(`[WebRTC Debug] Call details - Caller: ${{caller}}, Type: ${{callType}}, ID: ${{invitationId}}`);
                console.log('[WebRTC Debug] Current state before updating:', {{
                    show_incoming_call: state.show_incoming_call,
                    incoming_caller: state.incoming_caller,
                    call_type: state.call_type
                }});
                
                // Update state immediately
                state.current_chat_user = caller;
                state.call_type = callType;
                state.show_incoming_call = true;
                state.call_invitation_id = invitationId;
                state.incoming_caller = caller;
                
                try {{
                    // Create and play ringtone
                    if (!window.ringtoneElement) {{
                        window.ringtoneElement = new Audio('/static/ringtone.mp3');
                        window.ringtoneElement.loop = true;
                        window.ringtoneElement.volume = 0.7;
                    }}
                    
                    // Try to play ringtone
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
                
                // Flash title
                const origTitle = document.title;
                window.titleFlashInterval = setInterval(() => {{
                    document.title = document.title === origTitle ? 
                        `📞 Incoming ${{callType === 'video' ? 'Video' : 'Audio'}} Call from ${{caller}}` : origTitle;
                }}, 1000);
                
                // Force UI update with small delay
                setTimeout(() => {{
                    console.log('[WebRTC Debug] Force updating UI state for incoming call');
                    state._update();
                }}, 100);
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
    async def start_call(self):
        """Start an audio call with the current chat user."""
        print("[WebRTC Debug] Starting audio call initialization")
        
        # Verify we have someone to call
        if not self.current_chat_user or not self.current_room_id:
            self.error_message = "No active chat user or room"
            print("[WebRTC Debug] Error: No active chat user or room")
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            self.error_message = "Not authenticated"
            print("[WebRTC Debug] Error: Not authenticated")
            return
            
        # Get user ID and room name for call API
        current_username = await self.get_current_username()
        current_user_id = await self.get_storage_item("user_id")
        room_id = str(self.current_room_id)
        
        # Initialize WebRTC component
        await self.initialize_peer_connection()
        
        # Show calling popup
        self.call_type = "audio"
        self.show_calling_popup = True
        
        try:
            print(f"[WebRTC Debug] Initializing peer connection")
            
            # Send API request to create call notification
            api_url = f"{self.API_BASE_URL}/incoming-calls/"
            
            print(f"[WebRTC Debug] Sending start call notification to server")
            
            # Use JavaScript fetch for API call to create call notification
            rx.call_script(f"""
                // Call API to create notification
                fetch('{api_url}', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer {self.auth_token}'
                    }},
                    body: JSON.stringify({{
                        'recipient_id': '{self.current_chat_user}',
                        'room_id': '{room_id}',
                        'call_type': 'audio'
                    }})
                }})
                .then(response => {{
                    console.log('[WebRTC Debug] Call start API status:', response.status);
                    if (response.ok) {{
                        return response.json();
                    }} else {{
                        throw new Error('Failed to create call notification: ' + response.status);
                    }}
                }})
                .then(data => {{
                    console.log('[WebRTC Debug] Call start API response:', data);
                    
                    // Store the notification ID for later use
                    state.call_invitation_id = data.id;
                    
                    // Send WebSocket message to announce call to all room users
                    if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                        console.log('[WebRTC Debug] Sending room-wide call announcement');
                        window.chatSocket.send(JSON.stringify({{
                            type: 'room_call_announcement',
                            room: '{room_id}',
                            room_name: '{self.current_room_name}',
                            caller_username: '{current_username}',
                            caller_id: '{current_user_id}',
                            call_type: 'audio',
                            invitation_id: data.id
                        }}));
                    }}
                    
                    console.log('[WebRTC Debug] Call started successfully');
                }})
                .catch(error => {{
                    console.error('[WebRTC Debug] Error starting call:', error);
                    state.error_message = 'Failed to start call: ' + error.message;
                    state.show_calling_popup = false;
                    state._update();
                }});
            """)
            
        except Exception as e:
            print(f"[WebRTC Debug] Error starting call: {str(e)}")
            self.error_message = f"Error starting call: {str(e)}"
            self.show_calling_popup = False

    @rx.event
    async def start_video_call(self):
        """Start a video call with the current chat user."""
        print("[WebRTC Debug] Starting video call initialization")
        
        # Verify we have someone to call
        if not self.current_chat_user or not self.current_room_id:
            self.error_message = "No active chat user or room"
            print("[WebRTC Debug] Error: No active chat user or room")
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            self.error_message = "Not authenticated"
            print("[WebRTC Debug] Error: Not authenticated")
            return
            
        # Get user ID and room name for call API
        current_username = await self.get_current_username()
        current_user_id = await self.get_storage_item("user_id")
        room_id = str(self.current_room_id)
        
        # Initialize WebRTC component
        await self.initialize_peer_connection()
        
        # Show calling popup
        self.call_type = "video"
        self.show_calling_popup = True
        
        try:
            print(f"[WebRTC Debug] Initializing peer connection for video call")
            
            # Send API request to create call notification
            api_url = f"{self.API_BASE_URL}/incoming-calls/"
            
            print(f"[WebRTC Debug] Sending start video call notification to server")
            
            # Use JavaScript fetch for API call to create call notification
            rx.call_script(f"""
                // Call API to create notification
                fetch('{api_url}', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer {self.auth_token}'
                    }},
                    body: JSON.stringify({{
                        'recipient_id': '{self.current_chat_user}',
                        'room_id': '{room_id}',
                        'call_type': 'video'
                    }})
                }})
                .then(response => {{
                    console.log('[WebRTC Debug] Video call start API status:', response.status);
                    if (response.ok) {{
                        return response.json();
                    }} else {{
                        throw new Error('Failed to create video call notification: ' + response.status);
                    }}
                }})
                .then(data => {{
                    console.log('[WebRTC Debug] Video call start API response:', data);
                    
                    // Store the notification ID for later use
                    state.call_invitation_id = data.id;
                    
                    // Send WebSocket message to announce call to all room users
                    if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                        console.log('[WebRTC Debug] Sending room-wide video call announcement');
                        window.chatSocket.send(JSON.stringify({{
                            type: 'room_call_announcement',
                            room: '{room_id}',
                            room_name: '{self.current_room_name}',
                            caller_username: '{current_username}',
                            caller_id: '{current_user_id}',
                            call_type: 'video',
                            invitation_id: data.id
                        }}));
                    }}
                    
                    console.log('[WebRTC Debug] Video call started successfully');
                }})
                .catch(error => {{
                    console.error('[WebRTC Debug] Error starting video call:', error);
                    state.error_message = 'Failed to start video call: ' + error.message;
                    state.show_calling_popup = false;
                    state._update();
                }});
            """)
            
            # Start tracking call duration
            await self.start_call_timer()
            
        except Exception as e:
            print(f"[WebRTC Debug] Error starting video call: {str(e)}")
            self.error_message = f"Error starting video call: {str(e)}"
            self.show_calling_popup = False
    
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
            api_url = f"{self.API_BASE_URL}/calls/end/"
            
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
    async def decline_call(self):
        """Decline an incoming call."""
        if not self.call_invitation_id:
            self.error_message = "No active call invitation"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot decline call")
            self.error_message = "Not authenticated. Please log in."
            return
            
        try:
            # 1. Stop ringtone and clean up notification state
            rx.call_script("""
                // Stop ringtone if playing
                if (window.ringtoneElement) {
                    window.ringtoneElement.pause();
                    window.ringtoneElement.currentTime = 0;
                }
                
                // Stop title flashing
                if (window.titleFlashInterval) {
                    clearInterval(window.titleFlashInterval);
                    document.title = document.title.replace('📞 Incoming Call', 'Chat');
                }
            """)
            
            # 2. Send call response to server
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/communication/call-response/",
                    json={
                        "invitation_id": self.call_invitation_id,
                        "response": "decline"
                    },
                    headers=headers,
                    follow_redirects=True
                )
                
                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to decline call: {response.status_code}")
                
                if self.debug_log_api_calls:
                    print(f"Call decline API response: {response.status_code}")
            
            # 3. Also send response via WebSocket
            rx.call_script(f"""
                // Send call response over WebSocket
                if (window.chatSocket && window.chatSocket.readyState === WebSocket.OPEN) {{
                    window.chatSocket.send(JSON.stringify({{
                        type: 'call_response',
                        invitation_id: '{self.call_invitation_id}',
                        response: 'decline'
                    }}));
                }}
            """)
            
            # 4. Clean up state
            self.show_incoming_call = False
            self.call_invitation_id = ""
            self.incoming_caller = ""
            self.call_type = "audio"
            
        except Exception as e:
            self.error_message = f"Error declining call: {str(e)}"
            print(f"Error declining call: {str(e)}")
            # Still clean up state even if there's an error
            self.show_incoming_call = False
            self.call_invitation_id = ""

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
    async def join_existing_call(self):
        """Join an existing call in the current room."""
        print("[WebRTC Debug] Joining existing call in room")
        
        # Check if we have an active room call to join
        if not self.active_room_call:
            self.error_message = "No active call to join"
            print("[WebRTC Debug] Error: No active call to join")
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            self.error_message = "Not authenticated"
            print("[WebRTC Debug] Error: Not authenticated")
            return
            
        # Set call type from active room call
        call_type = self.active_room_call.get("call_type", "audio")
        room_id = self.active_room_call.get("room_id", "")
        caller = self.active_room_call.get("caller", "")
        
        # Ensure we're in the right room
        if str(self.current_room_id) != str(room_id):
            print(f"[WebRTC Debug] Need to switch to room {room_id} first")
            await self.open_room(room_id)
        
        print(f"[WebRTC Debug] Joining {call_type} call initiated by {caller}")
        
        # Connect to WebRTC signaling
        await self.connect_webrtc_signaling()
        
        # Determine call type and set UI accordingly
        if call_type == "video":
            print("[WebRTC Debug] Setting up video call UI for joining")
            self.show_video_popup = True
            
            # Initialize media with video
            rx.call_script("""
                console.log('[WebRTC Debug] Initializing video call media for joining call');
                
                // Get user media with video
                navigator.mediaDevices.getUserMedia({ audio: true, video: true })
                    .then(stream => {
                        console.log('[WebRTC Debug] Got local media stream with video');
                        
                        // Save stream reference
                        window.localStream = stream;
                        
                        // Display local video
                        const localVideo = document.getElementById('local-video');
                        if (localVideo) {
                            localVideo.srcObject = stream;
                        }
                        
                        // Let others know we joined
                        if (window.chatSocket) {
                            window.chatSocket.send(JSON.stringify({
                                type: 'join_call',
                                room_id: '""" + str(room_id) + """',
                                username: '""" + str(self.username) + """',
                                call_type: '""" + call_type + """'
                            }));
                        }
                        
                        // Update UI state
                        state.is_call_connected = true;
                        state.joining_existing_call = false;
                        state._update();
                    })
                    .catch(error => {
                        console.error('[WebRTC Debug] Error accessing media devices:', error);
                        state.error_message = 'Failed to access camera and microphone';
                        state.show_video_popup = false;
                        state._update();
                    });
            """)
        else:
            print("[WebRTC Debug] Setting up audio call UI for joining")
            self.show_call_popup = True
            
            # Initialize media with audio only
            rx.call_script("""
                console.log('[WebRTC Debug] Initializing audio call media for joining call');
                
                // Get user media with audio only
                navigator.mediaDevices.getUserMedia({ audio: true, video: false })
                    .then(stream => {
                        console.log('[WebRTC Debug] Got local media stream with audio');
                        
                        // Save stream reference
                        window.localStream = stream;
                        
                        // Let others know we joined
                        if (window.chatSocket) {
                            window.chatSocket.send(JSON.stringify({
                                type: 'join_call',
                                room_id: '""" + str(room_id) + """',
                                username: '""" + str(self.username) + """',
                                call_type: '""" + call_type + """'
                            }));
                        }
                        
                        // Update UI state
                        state.is_call_connected = true;
                        state.joining_existing_call = false;
                        state._update();
                    })
                    .catch(error => {
                        console.error('[WebRTC Debug] Error accessing microphone:', error);
                        state.error_message = 'Failed to access microphone';
                        state.show_call_popup = false;
                        state._update();
                    });
            """)
        
        # Start call timer
        await self.start_call_timer()

    @rx.event
    async def go_back_to_chat_list(self):
        """Go back to the chat list from a chat room."""
        print("Going back to chat list")
        # Clear the current room state
        self.current_room_id = ""
        self.current_chat_user = ""
        
        # Reset call-related states
        self.show_call_popup = False
        self.show_video_popup = False
        self.show_calling_popup = False
        self.show_incoming_call = False
        self.active_room_call = {}
        self.is_call_connected = False
        
        # Clean up WebRTC resources
        rx.call_script("""
            // Clean up WebRTC resources when going back to chat list
            console.log('[WebRTC Debug] Cleaning up resources when leaving room');
            
            // Stop local streams
            if (window.localStream) {
                window.localStream.getTracks().forEach(track => track.stop());
                window.localStream = null;
            }
            
            // Close peer connection
            if (window.peerConnection) {
                window.peerConnection.close();
                window.peerConnection = null;
            }
            
            // Clean up call handler resources
            if (window.callHandler && typeof window.callHandler.cleanupCall === 'function') {
                window.callHandler.cleanupCall();
            }
        """)
        
        # Redirect to the chat list
        return rx.redirect("/chat")

    @rx.event
    async def keypress_handler(self, key: str):
        """Handle keypress events in the message input."""
        try:
            # Only send typing notification for non-Enter keys
            if key != "Enter":
                # Send typing notification
                await self.send_typing_notification()
            # Send message when Enter is pressed
            elif key == "Enter" and self.message.strip():
                print(f"Sending message via Enter key: {self.message[:20]}...")
                # Use regular send_message, it will update the UI
                await self.send_message()
        except Exception as e:
            print(f"Error in keypress_handler: {e}")
            self.error_message = f"Error sending message: {e}"

    @rx.event
    async def toggle_mute(self):
        """Toggle microphone mute state."""
        self.is_muted = not self.is_muted
        
        # Update local stream audio tracks
        rx.call_script("""
            console.log('[WebRTC Debug] Toggling mute:', state.is_muted);
            
            // Toggle audio tracks in local stream
            if (window.localStream) {
                window.localStream.getAudioTracks().forEach(track => {
                    track.enabled = !state.is_muted;
                    console.log('[WebRTC Debug] Audio track enabled:', !state.is_muted);
                });
            }
        """)

    @rx.event
    async def toggle_camera(self):
        """Toggle camera on/off state."""
        self.is_camera_off = not self.is_camera_off
        
        # Update local stream video tracks
        rx.call_script("""
            console.log('[WebRTC Debug] Toggling camera:', state.is_camera_off);
            
            // Toggle video tracks in local stream
            if (window.localStream) {
                window.localStream.getVideoTracks().forEach(track => {
                    track.enabled = !state.is_camera_off;
                    console.log('[WebRTC Debug] Video track enabled:', !state.is_camera_off);
                });
            }
        """)
        
    @rx.event
    async def start_call_timer(self):
        """Start the call timer to track call duration."""
        print("[WebRTC Debug] Starting call timer")
        
        # Reset call duration
        self.call_duration = 0
        
        # Use JavaScript to increment the timer every second
        rx.call_script("""
            // Clear any existing timer
            if (window.callDurationTimer) {
                clearInterval(window.callDurationTimer);
            }
            
            // Start a new timer that updates every second
            window.callDurationTimer = setInterval(() => {
                // Only increment if call is active
                if (state.show_call_popup || state.show_video_popup) {
                    state.call_duration += 1;
                    state._update();
                } else {
                    // Stop timer if call is no longer active
                    clearInterval(window.callDurationTimer);
                }
            }, 1000);
        """)

    @rx.event
    async def clear_error_message(self):
        """Clear the error message."""
        self.error_message = ""
        
    @rx.event
    async def clear_success_message(self):
        """Clear the success message."""
        self.success_message = ""

    @rx.event
    async def show_error(self):
        """Show error message in a notification."""
        # This method is called when the error alert component mounts
        # No action needed as the error_message is already set before mounting
        pass
        
    @rx.event
    async def show_success(self):
        """Show success message in a notification."""
        # This method is called when the success alert component mounts
        # No action needed as the success_message is already set before mounting
        pass

    @rx.event
    async def login_as_user(self, username: str):
        """Debug function to set the current username manually."""
        print(f"Setting username to: {username}")
        
        # Update username in state
        self.username = username
        
        # Update in localStorage with direct script code
        rx.call_script(f"""
            // Save username to localStorage
            localStorage.setItem('username', '{username}');
            console.log('[Debug] Username saved to localStorage:', '{username}');
        """)
        
        # Show success message
        self.success_message = f"Logged in as {username}"

    @rx.event
    async def toggle_debug_info(self):
        """Toggle the visibility of the debug info panel."""
        print(f"Toggling debug info panel: {not self.debug_show_info}")
        self.debug_show_info = not self.debug_show_info

    @rx.event
    async def toggle_debug_dummy_data(self):
        """Toggle between using dummy data and real API data."""
        self.debug_use_dummy_data = not self.debug_use_dummy_data
        print(f"Debug dummy data set to: {self.debug_use_dummy_data}")
        
        # Reload data with the new setting
        if self.debug_use_dummy_data:
            await self._set_dummy_data()
            if hasattr(self, '_set_dummy_messages'):
                self._set_dummy_messages()
        else:
            try:
                # Load real data from the API
                # These methods should be implemented elsewhere
                if hasattr(self, 'load_rooms'):
                    await self.load_rooms()
                if self.current_room_id and hasattr(self, 'load_messages'):
                    await self.load_messages()
            except Exception as e:
                print(f"Error loading data: {e}, falling back to dummy data")
                await self._set_dummy_data()
                if hasattr(self, '_set_dummy_messages'):
                    self._set_dummy_messages()
                    
        # Show confirmation message
        self.success_message = f"Debug data mode: {'Dummy' if self.debug_use_dummy_data else 'API'}"

    @rx.event
    async def accept_call(self):
        """Accept an incoming call invitation."""
        print("[WebRTC Debug] Accepting incoming call")
        
        # Verify we have active call invitation
        if not self.call_invitation_id:
            self.error_message = "No active call invitation"
            print("[WebRTC Debug] Error: No active call invitation")
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        if not self.auth_token:
            self.error_message = "Not authenticated"
            print("[WebRTC Debug] Error: Not authenticated")
            return
            
        # Clean up notification state
        rx.call_script("""
            console.log('[WebRTC Debug] Cleaning up call notification state');
            
            // Stop ringtone if playing
            if (window.callHandler && typeof window.callHandler.stopRingtone === 'function') {
                window.callHandler.stopRingtone();
            } else if (window.ringtoneElement) {
                window.ringtoneElement.pause();
                window.ringtoneElement.currentTime = 0;
            }
            
            // Stop title flashing
            if (window.callHandler && typeof window.callHandler.stopTitleFlashing === 'function') {
                window.callHandler.stopTitleFlashing();
            } else if (window.titleFlashInterval) {
                clearInterval(window.titleFlashInterval);
                document.title = 'Chat';
            }
        """)
        
        # Set UI state for the appropriate call type
        self.show_incoming_call = False
        if self.call_type == "video":
            self.show_video_popup = True
        else:
            self.show_call_popup = True
            
        # Connect to WebRTC signaling
        if hasattr(self, 'connect_webrtc_signaling'):
            await self.connect_webrtc_signaling()
            
        # Start call timer
        if hasattr(self, 'start_call_timer'):
            await self.start_call_timer()

    @rx.event
    async def cleanup(self):
        """Clean up resources when component unmounts."""
        print("Cleaning up resources")
        
        # Clear any resource usage
        self.chat_history = []
        self.message = ""
        
        # Reset call-related states
        self.show_call_popup = False
        self.show_video_popup = False
        self.show_calling_popup = False
        self.show_incoming_call = False
        self.active_room_call = {}

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
                    # Call status
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
                        margin_bottom="10px",
                    ),
                    # Call duration - fix format string
                    # rx.text(
                    #     "Call time: " + str(ChatState.call_duration // 60) + ":" + str(ChatState.call_duration % 60),
                    #     color="gray.500",
                    #     font_size="18px",
                    #     margin_bottom="15px",
                    # ),
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
                        rx.button(
                            rx.icon("volume-2"),
                            # Fix: Replace lambda with a valid event handler or remove on_click
                            # on_click=lambda: None,  # This was causing the error
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
                        spacing="4",
                    ),
                    align_items="center",
                    justify_content="center",
                ),
                width="340px",
                height="450px",
                bg="white",
                border_radius="20px",
                padding="30px",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
                z_index="1000",
            ),
            # Remove the on_mount call since we're now handling timer separately
            # on_mount=ChatState.increment_call_duration,
        ),
    )

def video_call_popup() -> rx.Component:
    return rx.cond(
        ChatState.show_video_popup,
        rx.box(
            rx.center(
                rx.vstack(
                    rx.box(
                        rx.html("""
                            <div class="video-container" style="position: relative; width: 100%; height: 300px; background-color: #000; border-radius: 10px; overflow: hidden;">
                                <video id="remote-video" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
                                <div class="local-video-container" style="position: absolute; bottom: 10px; right: 10px; width: 120px; height: 90px; border-radius: 5px; overflow: hidden; border: 2px solid white;">
                                    <video id="local-video" autoplay playsinline muted style="width: 100%; height: 100%; object-fit: cover;"></video>
                                </div>
                            </div>
                        """),
                        width="100%",
                        height="300px",
                        margin_bottom="20px",
                    ),
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
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
                        spacing="4",
                    ),
                    # Add connection status indicator
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
                        margin_top="10px",
                    ),
                    # Call duration with fixed format
                    rx.text(
                        "Call time: " + str(ChatState.call_duration // 60) + ":" + str(ChatState.call_duration % 60),
                        color="gray.500",
                        font_size="14px",
                    ),
                    align_items="center",
                    justify_content="center",
                    width="100%",
                ),
                width="600px",
                height="500px",
                bg="white",
                border_radius="20px",
                padding="30px",
                position="fixed",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
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

def chat_page() -> rx.Component:
    return rx.box(
        rx.html("<script src='/static/call_handler.js'></script>"),
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