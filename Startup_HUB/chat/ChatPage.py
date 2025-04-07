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
            
            # 4. Update the URL to reflect the current room
            # Only update URL if we're not already on this room's URL
            if hasattr(self, "router"):
                current_params = getattr(self.router.page, "params", {})
                current_room_id = current_params.get("room_id", "")
                
                if current_room_id != room_id:
                    print(f"Updating URL to /chat/room/{room_id}")
                    return rx.redirect(f"/chat/room/{room_id}")
        except Exception as e:
            print(f"Error loading messages: {str(e)}")
            self.error_message = f"Failed to load messages: {str(e)}"

    @rx.event
    async def create_direct_chat(self, username: str):
        """Create or open a direct chat with a user."""
        print(f"\n===== Creating direct chat with user: {username} =====")
        
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot create chat")
            self.error_message = "Not authenticated. Please log in."
            return
            
        try:
            print(f"Checking if direct room already exists with {username}")
            
            # Set up headers
            headers = {
                "Authorization": f"Token {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            # Use AsyncClient for HTTP requests
            async with httpx.AsyncClient() as client:
                # Check if room already exists
                response = await client.get(
                    f"{self.API_BASE_URL}/communication/find-direct-room/?username={username}",
                    headers=headers,
                    follow_redirects=True
                )
                
                print(f"Find room response status: {response.status}") 
                data = response.json()
                print(f"Find room response data: {data}")
                
                if "room" in data and data["room"]:
                    # Room exists, open it
                    room = data["room"]
                    room_id = room.get("id")
                    print(f"Found existing room: {room_id}")
                    await self.open_room(room_id, username)
                else:
                    # Create new direct room
                    print(f"No existing room found, creating new one with {username}")
                    create_response = await client.post(
                        f"{self.API_BASE_URL}/communication/room/direct/",
                        json={"username": username},
                        headers=headers,
                        follow_redirects=True
                    )
                    
                    print(f"Create room response status: {create_response.status}")
                    room_data = create_response.json()
                    print(f"Create room response data: {room_data}")
                    
                    room_id = room_data.get("id")
                    if not room_id:
                        print("No room ID returned in response")
                        self.error_message = "Failed to create chat room - no room ID returned"
                        return
                        
                    print(f"Created new room with ID: {room_id}")
                    # Ensure current_room_id is set before loading messages
                    self.current_room_id = room_id
                    await self.open_room(room_id, username)
                    
                # Reload rooms list
                await self.load_rooms()
        except Exception as e:
            print(f"Error creating direct chat: {str(e)}")
            self.error_message = f"Error creating direct chat: {str(e)}"

    @rx.event
    async def start_call(self):
        """Start an audio call in the current room."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot start call")
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
                # Notify server about call start
                response = await client.post(
                    f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/start_call/",
                    json={"call_type": "audio"},
                    headers=headers,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    self.show_call_popup = True
                    self.call_duration = 0
                    self.show_calling_popup = True
                    self.call_type = "audio"
                    asyncio.create_task(self.increment_call_duration())
                else:
                    self.error_message = "Failed to start call"
        except Exception as e:
            self.error_message = f"Error starting call: {str(e)}"

    @rx.event
    async def start_video_call(self):
        """Start a video call in the current room."""
        if not self.current_room_id:
            self.error_message = "No active chat room"
            return
            
        # Get authentication token
        self.auth_token = await self.get_token()
        
        if not self.auth_token:
            print("Not authenticated - cannot start video call")
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
                # Notify server about call start
                response = await client.post(
                    f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/start_call/",
                    json={"call_type": "video"},
                    headers=headers,
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    self.show_video_popup = True
                    self.show_calling_popup = True
                    self.call_type = "video"
                    asyncio.create_task(self.increment_call_duration())
                else:
                    self.error_message = "Failed to start video call"
        except Exception as e:
            self.error_message = f"Error starting video call: {str(e)}"

    @rx.event
    async def end_call(self):
        self.show_call_popup = False
        self.show_calling_popup = False
        
        # Notify server about call end
        if self.current_room_id:
            try:
                # Get authentication token
                self.auth_token = await self.get_token()
                
                if not self.auth_token:
                    print("Not authenticated - cannot end call properly")
                    return
                    
                # Set up headers
                headers = {
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
                
                # Use AsyncClient for HTTP requests
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/end_call/",
                        headers=headers,
                        follow_redirects=True
                    )
            except Exception:
                pass  # Silently fail
        yield

    @rx.event
    async def end_video_call(self):
        self.show_video_popup = False
        self.show_calling_popup = False
        
        # Notify server about call end
        if self.current_room_id:
            try:
                # Get authentication token
                self.auth_token = await self.get_token()
                
                if not self.auth_token:
                    print("Not authenticated - cannot end call properly")
                    return
                    
                # Set up headers
                headers = {
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
                
                # Use AsyncClient for HTTP requests
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/end_call/",
                        headers=headers,
                        follow_redirects=True
                    )
            except Exception:
                pass  # Silently fail
        yield

    @rx.event
    async def toggle_mute(self):
        self.is_muted = not self.is_muted
        yield

    @rx.event
    async def toggle_camera(self):
        self.is_camera_off = not self.is_camera_off
        yield

    @rx.event
    async def increment_call_duration(self):
        while self.show_call_popup or self.show_video_popup:
            self.call_duration += 1
            yield rx.utils.sleep(1)

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
    async def go_back_to_chat_list(self):
        """Go back to the chat list from a chat room."""
        print("Going back to chat list")
        # Clear the current room state
        self.current_room_id = ""
        self.current_chat_user = ""
        
        # Redirect to the chat list
        return rx.redirect("/chat")

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

def calling_popup() -> rx.Component:
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
                    ),
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="20px",
                    ),
                    rx.text(
                        "Calling...",
                        font_size="18px",
                        color="#666666",
                        margin_bottom="20px",
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
                    align_items="center",
                    justify_content="center",
                ),
                width=rx.cond(
                    ChatState.call_type == "video",
                    "500px",
                    "300px"
                ),
                height="400px",
                bg="white",
                border_radius="20px",
                padding="30px",
                position="fixed",
                top="50%",
                left="30%",
                transform="translate(-50%, -50%)",
                box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
                z_index="1000",
            ),
        ),
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
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="20px",
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
                            color="gray",
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
                    align_items="center",
                    justify_content="center",
                ),
                width="300px",
                height="400px",
                bg="white",
                border_radius="20px",
                padding="30px",
                position="fixed",
                top="50%",
                left="70%",
                transform="translate(-50%, -50%)",
                box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
                z_index="1000",
            ),
            on_mount=ChatState.increment_call_duration,
        ),
    )

def video_call_popup() -> rx.Component:
    return rx.cond(
        ChatState.show_video_popup,
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
                    rx.text(
                        ChatState.current_chat_user,
                        font_size="24px",
                        font_weight="bold",
                        color="#333333",
                        margin_bottom="20px",
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
                            color="gray",
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
                    align_items="center",
                    justify_content="center",
                ),
                width="500px",
                height="400px",
                bg="white",
                border_radius="20px",
                padding="30px",
                position="fixed",
                top="50%",
                left="70%",
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
    # Just check if the message string starts with "/_upload"
    # Without using rx.is_instance since it doesn't exist in this Reflex version
    is_upload = rx.cond(
        message.startswith("/_upload"),
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
                        src=rx.cond(message != "", message, ""),
                        max_width="200px",
                        border_radius="15px"
                    ),
                    rx.text(
                        rx.cond(message != "", message, ""), 
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
                    font_size="lg",
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
                    font_size="lg",
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
        # Display current username
        # rx.text(
        #     f"(Logged in as: {ChatState.username})",
        #     color="rgba(255, 255, 255, 0.7)",
        #     font_size="12px",
        #     margin_left="2",
        # ),
        # rx.button(
        #     "Test as Tester",
        #     on_click=ChatState.login_as_user("Tester"),
        #     bg="rgba(255, 255, 255, 0.2)",
        #     color="white",
        #     border_radius="md",
        #     padding="0 8px",
        #     height="24px",
        #     font_size="xs",
        #     margin_left="2",
        #     _hover={
        #         "bg": "rgba(255, 255, 255, 0.3)",
        #     },
        #     transition="all 0.2s ease-in-out",
        # ),
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

def chat_page() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.cond(
                ChatState.sidebar_visible,
                sidebar(),
                rx.fragment()
            ),
            rooms_list(),
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