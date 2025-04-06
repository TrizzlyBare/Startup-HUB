import reflex as rx
import json
import asyncio
from typing import List, Dict, Optional, Any
from ..Matcher.SideBar import sidebar

class ChatState(rx.State):
    # API settings
    API_BASE_URL: str = "http://startup-hub:8000/api"
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
    
    # WebSocket connection status
    is_connected: bool = False
    reconnecting: bool = False
    should_reconnect: bool = True
    last_message_time: float = 0
    
    # UI state
    sidebar_visible: bool = True
    
    # Login state
    username: str = ""

    @rx.var
    def is_authenticated(self) -> bool:
        return self.auth_token != ""
        
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
    async def on_mount(self):
        """Initialize when the component mounts."""
        print("\n=== ChatPage Mounted ===")
        
        # Try to get token from local storage
        try:
            token = await rx.call_script("localStorage.getItem('auth_token')")
            if token:
                print(f"Found auth token in localStorage: {token[:5]}...")
                self.auth_token = token
                await self.load_rooms()
            else:
                # Try alternative methods to get the token
                token = rx.get_local_storage("auth_token")
                if token:
                    print(f"Found auth token via get_local_storage: {token[:5]}...")
                    self.auth_token = token
                    await self.load_rooms()
                else:
                    # Redirect to login or show login form
                    print("No auth token found - showing login form")
                    self.error_message = "Please log in to access chat"
        except Exception as e:
            print(f"Error in ChatPage on_mount: {str(e)}")
            self.error_message = f"Error initializing chat: {str(e)}"

    @rx.event
    async def poll_messages(self):
        """Poll for new messages as a fallback for WebSockets."""
        if not self.current_room_id or not self.auth_token:
            return
            
        while self.should_reconnect:
            try:
                # Only poll if we haven't received a message recently
                current_time = asyncio.get_event_loop().time()
                if current_time - self.last_message_time > 2:  # If no messages in 2 seconds
                    response = await rx.http.get(
                        f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/messages/?since_timestamp={self.last_message_time}",
                        headers={"Authorization": f"Token {self.auth_token}"}
                    )
                    
                    data = response.json()
                    messages = data.get("results", [])
                    
                    for msg in messages:
                        sender = msg.get("sender", {}).get("username", "unknown")
                        content = msg.get("content", "")
                        sent_at = msg.get("sent_at", "")
                        
                        # Determine if the message is from the current user
                        is_current_user = sender == rx.get_local_storage("username")
                        
                        # Add to chat history if not already there
                        message_key = f"{sender}:{content}:{sent_at}"
                        if not any(message_key in str(msg) for msg in self.chat_history[-10:]):
                            self.chat_history.append(
                                ("user" if is_current_user else "other", content)
                            )
                
                # Update last message time
                self.last_message_time = current_time
            except Exception as e:
                self.error_message = f"Error polling messages: {str(e)}"
                
            # Wait 2 seconds before polling again
            await rx.utils.sleep(2)

    @rx.event
    async def login(self, username: str, password: str = ""):
        """Login user to get authentication token."""
        try:
            response = await rx.http.post(
                f"{self.API_BASE_URL}/communication/login/",
                json={"username": username},  # Password not needed as per API description
                headers={"Content-Type": "application/json"}
            )
            
            data = response.json()
            if "token" in data:
                self.auth_token = data["token"]
                rx.set_local_storage("auth_token", self.auth_token)
                rx.set_local_storage("username", username)
                self.success_message = "Login successful"
                await self.load_rooms()
            else:
                self.error_message = "Failed to login"
        except Exception as e:
            self.error_message = f"Login error: {str(e)}"

    @rx.event
    async def load_rooms(self):
        """Load all rooms for the current user."""
        if not self.auth_token:
            self.error_message = "Not authenticated"
            return

        try:
            response = await rx.http.get(
                f"{self.API_BASE_URL}/communication/my-rooms/",
                headers={"Authorization": f"Token {self.auth_token}"}
            )
            
            data = response.json()
            self.rooms = data.get("rooms", [])
            
            # If we have rooms, set the first one as active
            if self.rooms and not self.current_room_id:
                first_room = self.rooms[0]
                self.current_room_id = first_room.get("id")
                self.current_chat_user = first_room.get("name", "Chat")
                await self.load_messages()
                
                # Start polling for messages as WebSocket alternative
                self.should_reconnect = True
                self.last_message_time = asyncio.get_event_loop().time()
                asyncio.create_task(self.poll_messages())
        except Exception as e:
            self.error_message = f"Error loading rooms: {str(e)}"

    @rx.event
    async def load_messages(self):
        """Load messages for the current room."""
        if not self.auth_token or not self.current_room_id:
            return

        try:
            response = await rx.http.get(
                f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/messages/",
                headers={"Authorization": f"Token {self.auth_token}"}
            )
            
            data = response.json()
            messages = data.get("results", [])
            
            # Clear existing chat history
            self.chat_history = []
            
            # Format messages for display
            for msg in messages:
                sender = msg.get("sender", {}).get("username", "unknown")
                content = msg.get("content", "")
                
                # Determine if the message is from the current user
                is_current_user = sender == rx.get_local_storage("username")
                
                # Add to chat history
                self.chat_history.append(
                    ("user" if is_current_user else "other", content)
                )
                
            # Update last message time to now
            self.last_message_time = asyncio.get_event_loop().time()
        except Exception as e:
            self.error_message = f"Error loading messages: {str(e)}"

    @rx.event
    async def send_message(self):
        """Send a message to the current room."""
        if not self.message.strip() or not self.current_room_id:
            return
            
        try:
            # Add message to UI immediately for responsiveness
            self.chat_history.append(("user", self.message))
            message_to_send = self.message
            self.message = ""
            yield
            
            # Send via REST API
            response = await rx.http.post(
                f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/messages/",
                json={"content": message_to_send, "message_type": "text"},
                headers={
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code != 201:
                # If message failed to send, show error
                self.error_message = "Failed to send message"
            else:
                # Update last message time to now
                self.last_message_time = asyncio.get_event_loop().time()
        except Exception as e:
            self.error_message = f"Error sending message: {str(e)}"
    
    @rx.event
    async def send_typing_notification(self):
        """Send typing notification to other users."""
        if not self.current_room_id:
            return
            
        try:
            # Use REST API to send typing notification
            await rx.http.post(
                f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/typing/",
                headers={
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
            )
        except Exception:
            # Silently fail typing notifications
            pass

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
                
                media_response = await rx.http.post(
                    f"{self.API_BASE_URL}/communication/media/",
                    data=form_data,
                    headers={"Authorization": f"Token {self.auth_token}"}
                )
                
                media_data = media_response.json()
                media_id = media_data.get("id")
                
                # Send message with media
                message_data = {
                    "room_id": self.current_room_id,
                    "message_type": file_type,
                    f"{file_type}": media_id
                }
                
                await rx.http.post(
                    f"{self.API_BASE_URL}/communication/messages/",
                    json=message_data,
                    headers={
                        "Authorization": f"Token {self.auth_token}",
                        "Content-Type": "application/json"
                    }
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
            
        if not self.auth_token:
            print("Not authenticated - cannot open room")
            return

        # Set the room details
        self.current_room_id = room_id
        
        # Set room name if provided
        if room_name:
            self.current_chat_user = room_name
        else:
            # Try to find room name in the rooms list
            for room in self.rooms:
                if str(room.get("id", "")) == str(room_id):
                    self.current_chat_user = room.get("name", "Chat Room")
                    print(f"Found room name: {self.current_chat_user}")
                    break
            else:
                # Set a default name if not found
                self.current_chat_user = "Chat Room"
                print("Room not found in rooms list, using default name")
                
        print(f"Set current_room_id to {self.current_room_id} and current_chat_user to {self.current_chat_user}")
        
        # Load messages for this room
        try:
            await self.load_messages()
        except Exception as e:
            print(f"Error loading messages: {str(e)}")
            self.error_message = f"Failed to load messages: {str(e)}"

    @rx.event
    async def create_direct_chat(self, username: str):
        """Create or open a direct chat with a user."""
        print(f"\n===== Creating direct chat with user: {username} =====")
        
        if not self.auth_token:
            print("Not authenticated - cannot create chat")
            self.error_message = "Not authenticated"
            return
            
        try:
            print(f"Checking if direct room already exists with {username}")
            # Check if room already exists
            response = await rx.http.get(
                f"{self.API_BASE_URL}/communication/find-direct-room/?username={username}",
                headers={"Authorization": f"Token {self.auth_token}"}
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
                create_response = await rx.http.post(
                    f"{self.API_BASE_URL}/communication/room/direct/",
                    json={"username": username},
                    headers={
                        "Authorization": f"Token {self.auth_token}",
                        "Content-Type": "application/json"
                    }
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
            
        try:
            # Notify server about call start
            response = await rx.http.post(
                f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/start_call/",
                json={"call_type": "audio"},
                headers={
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
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
            
        try:
            # Notify server about call start
            response = await rx.http.post(
                f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/start_call/",
                json={"call_type": "video"},
                headers={
                    "Authorization": f"Token {self.auth_token}",
                    "Content-Type": "application/json"
                }
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
                await rx.http.post(
                    f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/end_call/",
                    headers={"Authorization": f"Token {self.auth_token}"}
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
                await rx.http.post(
                    f"{self.API_BASE_URL}/communication/rooms/{self.current_room_id}/end_call/",
                    headers={"Authorization": f"Token {self.auth_token}"}
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
        self.should_reconnect = False  # Stop polling
        yield

    @rx.event
    async def handle_room_click(self):
        """Handle click on a room - no-argument version needed by Reflex."""
        # We'll use a different approach without needing event data
        # We'll rely on the JavaScript to call our open_room method directly
        pass

    @rx.event
    async def open_room_1(self):
        """Open room 1."""
        # Open the first room in the formatted rooms list
        if self.formatted_rooms and len(self.formatted_rooms) > 0:
            room = self.formatted_rooms[0]
            await self.open_room(
                room.get("id", ""), 
                room.get("name", "Unknown Room")
            )
    
    @rx.event
    async def open_room_2(self):
        """Open room 2."""
        # Open the second room in the formatted rooms list
        if self.formatted_rooms and len(self.formatted_rooms) > 1:
            room = self.formatted_rooms[1]
            await self.open_room(
                room.get("id", ""), 
                room.get("name", "Unknown Room")
            )
    
    @rx.event
    async def open_room_3(self):
        """Open room 3."""
        # Open the third room in the formatted rooms list
        if self.formatted_rooms and len(self.formatted_rooms) > 2:
            room = self.formatted_rooms[2]
            await self.open_room(
                room.get("id", ""), 
                room.get("name", "Unknown Room")
            )

    @rx.event
    async def keypress_handler(self, key: str):
        """Handle keypress events in the message input."""
        # Only send typing notification for non-Enter keys
        if key != "Enter":
            await self.send_typing_notification()
        # Send message when Enter is pressed
        elif key == "Enter":
            await self.send_message()

    @rx.event
    async def show_error(self):
        """Show error message in a browser alert."""
        if self.error_message:
            await rx.window_alert(self.error_message)
        yield
        
    @rx.event
    async def show_success(self):
        """Show success message in a browser alert."""
        if self.success_message:
            await rx.window_alert(self.success_message)
        yield

    @rx.event
    async def find_existing_room(self, current_username, target_username):
        """Find an existing direct chat room between two users.
        
        Returns the room ID if found, otherwise None.
        """
        print(f"\n===== Finding existing room between {current_username} and {target_username} =====")
        
        if not self.auth_token:
            print("Not authenticated - cannot find room")
            return None
        
        try:
            print(f"Making API request to find direct room with {target_username}")
            # Call the API to find an existing direct room
            response = await rx.http.get(
                f"{self.API_BASE_URL}/communication/find-direct-room/?username={target_username}",
                headers={"Authorization": f"Token {self.auth_token}"}
            )
            
            print(f"Find room response status: {response.status}")
            data = response.json()
            print(f"Find room response data: {data}")
            
            # Check if a room was found
            if "room" in data and data["room"]:
                # Return the room ID
                room_id = data["room"].get("id")
                print(f"Found existing room: {room_id}")
                return room_id
            
            # No room found
            print("No existing room found")
            return None
        except Exception as e:
            print(f"Error finding existing room: {str(e)}")
            return None

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
                                # Now use a direct URL instead of an event handler
                                on_click=rx.redirect(f"/chat/room/{room.get('id', '')}"),
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
                            on_click=rx.window_alert("Create chat feature coming soon!"),
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
                            on_click=rx.window_alert("Create chat feature coming soon!"),
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

def login_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Login to Chat", size="3", color="white", margin_bottom="4"),
            rx.input(
                placeholder="Username",
                value=ChatState.username,
                on_change=ChatState.set_username,
                margin_bottom="3",
                bg="white",
                border="1px solid #80d0ea",
                border_radius="md",
                padding="2",
            ),
            rx.button(
                "Login",
                on_click=lambda: ChatState.login(ChatState.username),
                bg="#80d0ea",
                color="white",
                width="100%",
                _hover={"bg": "#6bc0d9"},
                padding_y="2",
                border_radius="md",
                margin_top="2",
            ),
            width="300px",
            padding="5",
            bg="#2d2d2d",
            border_radius="md",
            border="1px solid #444",
            margin="auto",
        ),
        width="100%",
        height="100vh",
        display="flex",
        justify_content="center",
        align_items="center",
        bg="#1e1e1e",
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

def user_header() -> rx.Component:
    return rx.hstack(
        # Back button - only show when in a chat
        rx.cond(
            ChatState.current_room_id != "",
            rx.button(
                rx.icon("arrow-left", color="white", font_size="18px"),
                on_click=rx.redirect("/chat"),
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

def message_display(sender: str, message: str) -> rx.Component:
    # Just check if the message string starts with "/_upload"
    # Without using rx.is_instance since it doesn't exist in this Reflex version
    is_upload = rx.cond(
        message.startswith("/_upload"),
        True,
        False
    )
    
    return rx.hstack(
        rx.cond(
            sender == "user",
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
                rx.text(rx.cond(message != "", message, ""), color="#333333")
            ),
            padding="10px 15px",
            border_radius="15px",
            max_width="70%",
            bg=rx.cond(
                sender == "user",
                "#80d0ea",
                "white"
            ),
            margin_left=rx.cond(
                sender == "user",
                "auto",
                "0"
            ),
            margin_right=rx.cond(
                sender == "user",
                "0",
                "auto"
            ),
            box_shadow="0px 1px 2px rgba(0, 0, 0, 0.1)",
        ),
        width="100%",
        margin_y="10px",
        padding_x="15px",
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

def chat_page() -> rx.Component:
    return rx.box(
        rx.cond(
            ChatState.is_authenticated,
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
            login_form(),
        ),
        calling_popup(),
        call_popup(),
        video_call_popup(),
        error_alert(),
        success_alert(),
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

def direct_chat_room_route() -> rx.Component:
    """Route handler for direct chat room with specific user.
    
    This route now just extracts the user info and passes to the room-based implementation.
    The room_id is always the primary identifier.
    """
    # Get URL parameters
    chat_user = rx.State.router.page.params.get("chat_user", "")
    room_id = rx.State.router.page.params.get("room_id", "")
    
    # This is useful for debugging
    print(f"Opening direct chat with user: {chat_user}, room_id: {room_id}")
    
    # Create a wrapper component with its own state
    class DirectChatWrapper(rx.Component):
        # Show loading state
        loading: bool = True
        error: str = ""
        
        def on_mount(self):
            """Called when the component mounts."""
            return self.on_direct_chat_load
            
        # Define the on_mount event without parameters
        @rx.event
        async def on_direct_chat_load(self):
            """Load the direct chat room when mounted."""
            print(f"Starting direct_chat_room_route on_mount handler for {chat_user}, {room_id}")
            
            try:
                # Check authentication first
                token = None
                try:
                    token = await rx.call_script("localStorage.getItem('auth_token')")
                    print(f"Found token in localStorage: {bool(token)}")
                except Exception as e:
                    print(f"Error getting token from localStorage: {str(e)}")
                
                if not token:
                    token = rx.get_local_storage("auth_token")
                    print(f"Tried get_local_storage for token: {bool(token)}")
                    
                if not token:
                    print("No auth token found - showing login form")
                    # Set auth token in ChatState to trigger login form
                    ChatState.auth_token = ""
                    self.error = "Please log in to use chat"
                    self.loading = False
                    return
                else:
                    # We have a token, set it in ChatState
                    print(f"Found auth token for direct chat: {token[:5]}...")
                    ChatState.auth_token = token
                
                # Validate room_id
                if not room_id:
                    print("No room ID specified")
                    self.error = "No room ID specified"
                    self.loading = False
                    return
                
                # Set the room details using ChatState
                ChatState.current_room_id = room_id
                ChatState.current_chat_user = chat_user
                
                # Load messages
                try:
                    await ChatState.load_messages()
                    print(f"Loaded messages for room {room_id}")
                except Exception as e:
                    print(f"Error loading messages: {str(e)}")
                    self.error = f"Error loading messages: {str(e)}"
                
                # Loading complete
                self.loading = False
            except Exception as e:
                print(f"Unexpected exception in direct_chat_room_route: {str(e)}")
                self.error = f"Error: {str(e)}"
                self.loading = False
        
        def build(self):
            """Build the component."""
            # Add a loading and error state
            return rx.cond(
                self.loading, 
                # Loading state
                rx.center(
                    rx.vstack(
                        rx.heading("Opening Chat...", size="lg"),
                        rx.spinner(size="xl", color="#80d0ea", thickness="4px"),
                        rx.text(f"Loading chat with {chat_user}..."),
                        rx.cond(
                            self.error != "",
                            rx.text(self.error, color="red"),
                            rx.text("", height="0px"), # Empty placeholder
                        ),
                        spacing="4",
                        padding="8",
                    ),
                    height="100vh",
                    width="100%",
                ),
                # Regular chat page
                rx.box(
                    chat_page(),
                )
            )
    
    # Return the wrapper component
    return DirectChatWrapper()

def chat_room_route() -> rx.Component:
    """Route handler for any chat room by ID.
    
    This is the primary route for all chat types - direct or group.
    """
    # Get URL parameters
    room_id = rx.State.router.page.params.get("room_id", "")
    
    # This is useful for debugging
    print(f"Opening chat room: {room_id}")
    
    # Create a wrapper component with its own state
    class ChatRoomWrapper(rx.Component):
        # Show loading state
        loading: bool = True
        error: str = ""
        
        def on_mount(self):
            """Called when the component mounts."""
            return self.on_room_load
            
        # Define the on_mount event without parameters
        @rx.event
        async def on_room_load(self):
            """Load the chat room when mounted."""
            print(f"Starting chat_room_route on_mount handler for room {room_id}")
            
            try:
                # Check authentication first
                token = None
                try:
                    token = await rx.call_script("localStorage.getItem('auth_token')")
                    print(f"Found token in localStorage: {bool(token)}")
                except Exception as e:
                    print(f"Error getting token from localStorage: {str(e)}")
                
                if not token:
                    token = rx.get_local_storage("auth_token")
                    print(f"Tried get_local_storage for token: {bool(token)}")
                
                if not token:
                    print("No auth token found - showing login form")
                    # Set auth token in ChatState to trigger login form
                    ChatState.auth_token = ""
                    self.error = "Please log in to use chat"
                    self.loading = False
                    return
                else:
                    # We have a token, set it in ChatState
                    print(f"Found auth token for chat: {token[:5]}...")
                    ChatState.auth_token = token
                
                # Validate room_id
                if not room_id:
                    print("No room ID specified - redirecting to main chat")
                    self.loading = False
                    return rx.redirect("/chat")
                
                # Load rooms first to make sure we have the latest data
                try:
                    await ChatState.load_rooms()
                    print(f"Loaded {len(ChatState.rooms)} rooms")
                except Exception as e:
                    print(f"Error loading rooms: {str(e)}")
                
                # Try to find room details in available rooms
                found_room = False
                for room in ChatState.rooms:
                    if str(room.get("id", "")) == room_id:
                        room_name = room.get("name", "Chat Room")
                        # Set the room info
                        ChatState.current_room_id = room_id
                        ChatState.current_chat_user = room_name
                        found_room = True
                        print(f"Found room in room list: {room_name}")
                        break
                        
                # If not found but we have a room ID, try to load it directly
                if not found_room and room_id:
                    # Set default name temporarily
                    ChatState.current_room_id = room_id
                    ChatState.current_chat_user = "Chat Room"
                    print(f"Room {room_id} not found in room list, using default name")
                    
                # Load the messages for this room
                try:
                    await ChatState.load_messages()
                    print(f"Loaded messages for room {room_id}")
                except Exception as e:
                    print(f"Error loading messages: {str(e)}")
                    self.error = f"Error loading messages: {str(e)}"
                
                # Loading complete
                self.loading = False
            except Exception as e:
                print(f"Unexpected exception in chat_room_route: {str(e)}")
                self.error = f"Error: {str(e)}"
                self.loading = False
        
        def build(self):
            """Build the component."""
            # Add a loading and error state
            return rx.cond(
                self.loading, 
                # Loading state
                rx.center(
                    rx.vstack(
                        rx.heading("Opening Chat Room...", size="lg"),
                        rx.spinner(size="xl", color="#80d0ea", thickness="4px"),
                        rx.text(f"Loading chat room {room_id}..."),
                        rx.cond(
                            self.error != "",
                            rx.text(self.error, color="red"),
                            rx.text("", height="0px"), # Empty placeholder
                        ),
                        spacing="4",
                        padding="8",
                    ),
                    height="100vh",
                    width="100%",
                ),
                # Regular chat page
                rx.box(
                    chat_page(),
                )
            )
    
    # Return the wrapper component
    return ChatRoomWrapper()

def chat_user_route() -> rx.Component:
    """Route handler for chat with a user by username only (without room ID).
    
    This will find or create a direct chat room with the specified user.
    """
    # Get URL parameters
    chat_user = rx.State.router.page.params.get("chat_user", "")
    
    # This is useful for debugging
    print(f"\n===== DEBUG: Finding or creating direct chat with user: {chat_user} =====")
    
    # Create a wrapper component with its own state
    class ChatUserWrapper(rx.Component):
        # Show loading state
        loading: bool = True
        error: str = ""
        
        def on_mount(self):
            """Called when the component mounts."""
            print(f"MOUNT: ChatUserWrapper for user {chat_user}")
            return self.on_chat_user_load
            
        # Define the on_mount event without parameters
        @rx.event
        async def on_chat_user_load(self):
            """Find or create a chat room with this user when mounted."""
            print(f"\n===== Starting chat_user_route on_mount handler for {chat_user} =====")
            
            try:
                # Check authentication first
                token = None
                try:
                    token = rx.get_local_storage("auth_token")
                    print(f"Token from local storage: {bool(token)}")
                except Exception as e:
                    print(f"Error getting token from local storage: {str(e)}")
                    
                if not token:
                    print("No auth token found - showing login form")
                    # Set auth token in ChatState to empty to show login form
                    ChatState.auth_token = ""
                    self.error = "Please log in to use chat"
                    self.loading = False
                    return
                else:
                    # We have a token, set it in ChatState
                    print(f"Found auth token: {token[:5]}...")
                    ChatState.auth_token = token
                
                # Continue with user check
                if not chat_user:
                    print("No chat user specified - showing main chat")
                    self.loading = False
                    return rx.redirect("/chat")
                    
                # Try to find existing room first
                current_username = None
                try:
                    current_username = rx.get_local_storage("username")
                    print(f"Current user: {current_username}, target: {chat_user}")
                except Exception as e:
                    print(f"Error getting username from local storage: {str(e)}")
                    current_username = "unknown"
                    
                if not current_username:
                    self.error = "Could not determine current user"
                    self.loading = False
                    return
                
                # First try loading rooms to ensure we have the latest data
                try:
                    await ChatState.load_rooms()
                except Exception as e:
                    print(f"Error loading rooms: {str(e)}")
                    self.error = f"Error loading rooms: {str(e)}"
                    self.loading = False
                    return
                
                # Now check for existing room
                existing_room = None
                try:
                    existing_room = await ChatState.find_existing_room(current_username, chat_user)
                    print(f"Existing room check result: {existing_room}")
                except Exception as e:
                    print(f"Error finding existing room: {str(e)}")
                    self.error = f"Error finding room: {str(e)}"
                    self.loading = False
                    return
                
                if existing_room:
                    # Room exists, redirect to it
                    print(f"Found existing room: {existing_room}")
                    self.loading = False
                    # Extract room_id properly whether it's just an ID or a full room object
                    room_id = existing_room
                    if isinstance(existing_room, dict):
                        room_id = existing_room.get("id")
                    return rx.redirect(f"/chat/room/{room_id}")
                else:
                    # Create new direct room
                    print(f"No existing room found, creating new chat with {chat_user}")
                    
                    try:
                        # Create a direct chat room
                        print(f"Calling ChatState.create_direct_chat with {chat_user}")
                        await ChatState.create_direct_chat(chat_user)
                        
                        # Check if room was created successfully
                        if ChatState.current_room_id:
                            room_id = ChatState.current_room_id
                            print(f"Created room successfully: {room_id}")
                            self.loading = False
                            return rx.redirect(f"/chat/room/{room_id}")
                        else:
                            # Show an error with more context
                            print("Room creation failed - no room ID set in ChatState")
                            self.error = f"Could not create chat with {chat_user} (no room ID returned)"
                            self.loading = False
                    except Exception as e:
                        # Show error with more details
                        print(f"Exception creating chat: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        self.error = f"Error creating chat: {str(e)}"
                        self.loading = False
            except Exception as e:
                print(f"Unexpected exception in chat_user_route: {str(e)}")
                self.error = f"Error: {str(e)}"
                self.loading = False
        
        def build(self):
            """Build the component."""
            # Always show some UI even in error states
            return rx.cond(
                self.loading, 
                # Loading state
                rx.center(
                    rx.vstack(
                        rx.heading("Opening Chat...", size="lg"),
                        rx.spinner(size="xl", color="#80d0ea", thickness="4px"),
                        rx.text(f"Finding or creating chat with {chat_user}..."),
                        rx.cond(
                            self.error != "",
                            rx.text(self.error, color="red"),
                            rx.text("", height="0px"), # Empty placeholder
                        ),
                        spacing="4",
                        padding="8",
                    ),
                    height="100vh",
                    width="100%",
                ),
                # Either error or chat page
                rx.cond(
                    self.error != "",
                    # Error state - show a friendly error
                    rx.center(
                        rx.vstack(
                            rx.heading("Chat Error", size="lg"),
                            rx.text(self.error, color="red"),
                            rx.button(
                                "Return to Chat", 
                                on_click=rx.redirect("/chat"),
                                color_scheme="blue",
                            ),
                            spacing="4",
                            padding="8",
                            bg="white",
                            border_radius="md",
                            box_shadow="lg",
                        ),
                        height="100vh",
                        width="100%",
                    ),
                    # Regular chat page - don't add on_mount here to avoid recursion
                    rx.box(
                        chat_page(),
                    )
                )
            )
    
    # Return the wrapper component
    return ChatUserWrapper()