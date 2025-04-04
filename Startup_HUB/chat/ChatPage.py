import reflex as rx
from ..Auth.AuthPage import AuthState
from ..webrtc.webrtc_state import WebRTCState
from ..webrtc.call_utils import (
    start_audio_call,
    start_video_call,
    end_call as end_webrtc_call,
    toggle_audio,
    toggle_video
)
from ..webrtc.webrtc_components import (
    calling_popup as webrtc_calling_popup,
    call_popup as webrtc_call_popup,
    video_call_popup as webrtc_video_call_popup,
    incoming_call_popup
)
import httpx
from typing import List, Dict, Any, Optional

# Define ChatState here instead of importing it
class ChatState(rx.State):
    # Initialize with type annotation as required
    chat_history: list[tuple[str, str]] = [
        ("other", "Hello there!"),
        ("user", "Hi, how are you?"),
        ("other", "I'm doing great, thanks for asking!"),
    ]
    message: str = ""
    current_chat_user: str = "Andy Collins"
    current_chat_user_id: str = "user123"
    show_call_popup: bool = False
    show_video_popup: bool = False
    call_duration: int = 0
    is_muted: bool = False
    is_camera_off: bool = False
    show_calling_popup: bool = False
    call_type: str = "audio"
    chat_error_message: str = ""
    
    @rx.var
    def route_username(self) -> str:
        """Get username from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            chat_user = params.get("chat_user", "")
            if chat_user:
                # Update the current chat user based on the URL
                self.current_chat_user_id = chat_user  # Use chat_user as ID
                self.current_chat_user = chat_user     # Use chat_user directly
            return chat_user
        return ""
    
    @rx.var
    def route_group_id(self) -> str:
        """Get group_id from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            group_id = params.get("group_id", "")
            if group_id:
                # Update the current chat to a group chat
                self.current_chat_user_id = f"group_{group_id}"
                # In a real app, you would fetch the group name based on ID
                self.current_chat_user = f"Group {group_id}"
            return group_id
        return ""
    
    async def on_mount(self):
        """Called when the component is mounted."""
        # Check for route parameters on mount
        _ = self.route_username
        _ = self.route_group_id

    @rx.event
    async def send_message(self):
        """Send a message to the current chat."""
        print("=== Starting send_message ===")
        if not self.message.strip():
            print("Message is empty, returning")
            return

        try:
            # Get username from AuthState
            username = AuthState.username
            print(f"Current username: {username}")
            
            # Use rx.cond to handle the username check
            # Check if username is empty or None using rx.cond
            if rx.cond((username == "") | (username == None), True, False):
                print("Username is empty or None")
                self.chat_error_message = "Username missing, please log in"
                return

            # Get the current room ID from ChatRoomState
            room_state = ChatRoomState.get_state()
            room_id = room_state.current_room_id
            print(f"Current room ID: {room_id}")
            
            if not room_id:
                print("No room ID found")
                self.chat_error_message = "Cannot send message: Room not found"
                return
            
            # Optimistically update UI
            print(f"Adding message to chat history: {self.message}")
            self.chat_history.append(("user", self.message))
            message_content = self.message
            self.message = ""
            yield
            
            # Send message to API
            print("Sending message to API...")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://startup-hub:8000/api/communication/messages/",
                    headers={"Content-Type": "application/json"},
                    json={
                        "content": message_content,
                        "message_type": "text",
                        "room": room_id,
                        "sender": username,  # Add sender username
                        "is_read": False
                    }
                )
                
                print(f"API Response Status: {response.status_code}")
                print(f"API Response Text: {response.text}")
                
                if response.status_code not in (200, 201):
                    print(f"Failed to send message: {response.status_code} {response.text}")
                    self.chat_error_message = f"Failed to send message: {response.status_code} {response.text}"
                    # Remove the optimistic update if the API call fails
                    if len(self.chat_history) > 0:
                        print("Removing optimistic update due to API failure")
                        self.chat_history.pop()
        except Exception as e:
            print(f"Error in send_message: {str(e)}")
            self.chat_error_message = f"Error sending message: {str(e)}"
            # Remove the optimistic update
            if len(self.chat_history) > 0:
                print("Removing optimistic update due to error")
                self.chat_history.pop()
        finally:
            print("=== End of send_message ===")



    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle the upload of file(s).
        Args:
            files: The uploaded files.
        """
        for file in files:
            # The file data is already in bytes format
            upload_data = file
            outfile = rx.get_upload_dir() / file.filename
            # Save the file.
            with outfile.open("wb") as file_object:
                file_object.write(upload_data)
            # Update the chat history with file URL
            file_url = rx.get_upload_url(file.filename)
            self.chat_history.append(("user", file_url))
            yield

    @rx.event
    async def audio_call(self):
        """Start a WebRTC audio call"""
        print("Starting audio call from ChatState")
        # Use WebRTC for audio call
        webrtc_state = WebRTCState.get_state()
        webrtc_state.start_call(self.current_chat_user_id, is_video=False)
        webrtc_state.add_participant(self.current_chat_user_id, self.current_chat_user)
        webrtc_state.is_call_initiator = True
        await webrtc_state.initialize_webrtc()
        await webrtc_state.connect_to_signaling_server()
        yield
        
    @rx.event
    async def video_call(self):
        """Start a WebRTC video call"""
        print("Starting video call from ChatState")
        # Use WebRTC for video call
        webrtc_state = WebRTCState.get_state()
        webrtc_state.start_call(self.current_chat_user_id, is_video=True)
        webrtc_state.add_participant(self.current_chat_user_id, self.current_chat_user)
        webrtc_state.is_call_initiator = True
        await webrtc_state.initialize_webrtc()
        await webrtc_state.connect_to_signaling_server()
        yield

    @rx.event
    async def toggle_mute(self):
        # Use WebRTC to toggle audio
        await WebRTCState.toggle_audio()
        # Update local state for UI
        self.is_muted = not self.is_muted
        yield

    @rx.event
    async def toggle_camera(self):
        # Use WebRTC to toggle video
        await WebRTCState.toggle_video()
        # Update local state for UI
        self.is_camera_off = not self.is_camera_off
        yield

    @rx.event
    async def increment_call_duration(self):
        while self.show_call_popup:
            self.call_duration += 1
            yield rx.utils.sleep(1)

    @rx.event
    async def end_call(self):
        self.show_call_popup = False
        self.show_calling_popup = False
        yield

# Define model classes outside of ChatRoomState to avoid nesting issues
class RoomParticipantUser(rx.Base):
    username: str
    
class RoomParticipant(rx.Base):
    user: RoomParticipantUser
    
class RoomLastMessage(rx.Base):
    content: str

class Room(rx.Base):
    id: str
    name: str
    room_type: str
    profile_image: Optional[str] = None
    last_message: Optional[RoomLastMessage] = None
    participants: List[RoomParticipant]

class ChatRoomState(ChatState):
    """Extended chat state for handling room data from API"""
    rooms_data: List[Room] = []
    current_room_id: Optional[str] = None
    current_room_type: str = "direct"  # "direct" or "group"
    is_loading: bool = False
    room_error_message: str = ""
    show_create_group_modal: bool = False
    selected_participants: List[str] = []
    group_name: str = ""
    max_participants: int = 10
    
    @rx.event
    async def room_audio_call(self):
        """Start an audio call in the current room"""
        await self.initiate_call(False)
        
    @rx.event
    async def room_video_call(self):
        """Start a video call in the current room"""
        await self.initiate_call(True)
        
    def reset_state(self, preserve_username=False):
        """Reset the chat state."""
        # Store username if needed
        current_user = ""
        current_user_id = ""
        if preserve_username:
            current_user = self.current_chat_user
            current_user_id = self.current_chat_user_id
        
        # Reset message state
        self.chat_history = []
        self.message = ""
        self.room_error_message = ""
        self.is_loading = False
        
        # Reset room state but preserve user info if needed
        if preserve_username:
            self.current_chat_user = current_user
            self.current_chat_user_id = current_user_id
        else:
            self.current_chat_user = ""
            self.current_chat_user_id = ""
            self.current_room_id = None
            
        self.current_room_type = "direct"  # Default to direct messages
    
    def toggle_create_group_modal(self):
        """Toggle the create group modal"""
        self.show_create_group_modal = not self.show_create_group_modal
        
    def is_participant_selected(self, username: str) -> bool:
        """Check if a participant is selected for group chat"""
        for participant in self.selected_participants:
            if participant == username:
                return True
        return False
        
    @rx.event
    def toggle_participant(self, username: str):
        """Toggle a user in the selected participants list."""
        is_selected = False
        for participant in self.selected_participants:
            if participant == username:
                is_selected = True
                break
            
        if is_selected:
            # Remove the user from selected participants
            self.selected_participants = [p for p in self.selected_participants if p != username]
        else:
            # Add the user to selected participants
            self.selected_participants.append(username)
        
        return is_selected
    
    def set_group_name(self, name: str):
        """Set the group name"""
        self.group_name = name
        
    def set_max_participants(self, max_participants: str):
        """Set the maximum participants"""
        try:
            self.max_participants = int(max_participants)
        except ValueError:
            self.max_participants = 10
    
    @rx.var
    def chat_route_username(self) -> str:
        """Get username from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            chat_user = params.get("chat_user", "")
            if chat_user:
                # Update the current chat user based on the URL
                self.current_chat_user_id = chat_user  # Use chat_user as ID
                self.current_chat_user = chat_user     # Use chat_user directly
                self.current_room_type = "direct"
                # We'll load messages in initialize_chat
            return chat_user
        return ""
    
    @rx.var
    def chat_route_room_id(self) -> str:
        """Get room_id from route parameters."""
        if hasattr(self, "router"):
            params = getattr(self.router.page, "params", {})
            room_id = params.get("room_id", "")
            if room_id:
                # Update the current chat to a room chat
                self.current_room_id = room_id
                self.current_room_type = "group"
                # Find room name from rooms_data
                for room in self.rooms_data:
                    if room.id == room_id:
                        self.current_chat_user = room.name
                        break
                else:
                    # If room not found in data, set a default name and load data
                    self.current_chat_user = f"Group Chat"
                # We'll load messages in initialize_chat
            return room_id
        return ""
    
    async def on_mount(self):
        """Called when the component is mounted."""
        # Load rooms data on mount
        await self.load_rooms()
        # Check for route parameters on mount and initialize the chat
        await self.initialize_chat()
    
    @rx.event
    async def initialize_chat(self):
        """Initialize the chat based on route parameters."""
        try:
            # Get route parameters
            chat_user = self.chat_route_username
            room_id = self.chat_route_room_id
            
            # Load messages based on route parameters
            if chat_user:
                print(f"Initializing direct chat with user: {chat_user}")
                await self.load_direct_chat_messages(chat_user)
            elif room_id:
                print(f"Initializing room chat with ID: {room_id}")
                await self.load_room_messages(room_id)
        except Exception as e:
            self.room_error_message = f"Error initializing chat: {str(e)}"
            print(f"Error initializing chat: {str(e)}")
            
        return
    
    async def load_rooms(self):
        """Load chat rooms from the API"""
        self.is_loading = True
        auth_token = AuthState.token
        
        try:
            # Direct bitwise comparison for token validation
            if (auth_token == "") | (auth_token == None):
                print("Auth token is empty or None")
                self.room_error_message = "Authentication token missing"
                self.is_loading = False
                return
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://startup-hub:8000/api/communication/rooms/",
                    headers={"Authorization": f"Token {auth_token}"}
                )
                
                if response.status_code == 200:
                    # Convert the response to typed Room objects
                    rooms_json = response.json()
                    rooms = []
                    for room_data in rooms_json:
                        # Create properly typed Room objects
                        participants = []
                        for participant_data in room_data.get("participants", []):
                            user_data = participant_data.get("user", {})
                            user = RoomParticipantUser(
                                username=user_data.get("username", "")
                            )
                            participant = RoomParticipant(user=user)
                            participants.append(participant)
                        
                        # Handle last_message if it exists
                        last_message = None
                        if room_data.get("last_message"):
                            last_message = RoomLastMessage(
                                content=room_data.get("last_message", {}).get("content", "")
                            )
                        
                        room = Room(
                            id=room_data.get("id", ""),
                            name=room_data.get("name", ""),
                            room_type=room_data.get("room_type", ""),
                            profile_image=room_data.get("profile_image"),
                            last_message=last_message,
                            participants=participants
                        )
                        rooms.append(room)
                    
                    self.rooms_data = rooms
                    print(f"Loaded {len(rooms)} rooms")
                else:
                    self.room_error_message = f"Failed to load rooms: {response.status_code} {response.text}"
        except Exception as e:
            self.room_error_message = f"Error loading rooms: {str(e)}"
        finally:
            self.is_loading = False
    
    async def load_direct_chat_messages(self, username: str):
        """Load messages for direct chat with a user"""
        # Ensure username is a string value
        if not isinstance(username, str):
            username = str(username)
            
        print(f"load_direct_chat_messages called with username: {username}")
        
        # Store the username before any operations
        current_user = username
        
        # Reset chat history but preserve username
        self.reset_state(preserve_username=True)
        
        # Make sure the username is set correctly after reset
        self.current_chat_user = current_user
        self.current_chat_user_id = current_user
        self.current_room_type = "direct"
        
        self.is_loading = True
        auth_token = AuthState.token
        
        print(f"Direct chat username after setup: {self.current_chat_user}")
        
        try:
            # Direct bitwise comparison for token validation
            if rx.cond((auth_token == "") | (auth_token == None), True, False):
                print("Auth token is empty or None")
                self.room_error_message = "Authentication token missing"
                self.is_loading = False
                return
            
            # Find the room for this user
            room_id = None
            
            # First check if rooms_data is available and not empty
            if not self.rooms_data or len(self.rooms_data) == 0:
                # Load rooms first if they're not available
                print("No rooms data available, loading rooms first")
                await self.load_rooms()
                
            # Get the length of rooms_data safely
            rooms_count = len(self.rooms_data)
            
            # Safely iterate through rooms_data using index
            for room_idx in range(rooms_count):
                room = self.rooms_data[room_idx]
                if room.room_type == "direct":
                    # Get participants count safely
                    participants_count = len(room.participants)
                    
                    # Safely iterate through participants using index
                    for participant_idx in range(participants_count):
                        participant = room.participants[participant_idx]
                        # Debug info
                        print(f"Checking participant: {participant.user.username}, looking for: {username}")
                        if participant.user.username == username:
                            room_id = room.id
                            print(f"Found matching room ID: {room_id}")
                            break
                    if room_id:
                        break
            
            if not room_id:
                print(f"No room found for user: {username}")
                # Create a direct chat room since one doesn't exist
                print(f"Creating new direct chat with: {username}")
                # First attempt to create the direct chat
                await self.create_direct_chat(username)
                self.is_loading = False
                return
            
            # When loading room messages, pass the username to preserve it
            await self.load_room_messages_for_direct_chat(room_id, username)
            
        except Exception as e:
            self.room_error_message = f"Error loading direct chat messages: {str(e)}"
            print(f"Error in load_direct_chat_messages: {str(e)}")
            self.is_loading = False


    async def load_room_messages_for_direct_chat(self, room_id: str, username: str):
        """Load messages for a specific room while preserving the direct chat username"""
        self.chat_history = []
        self.is_loading = True
        auth_token = AuthState.token
        
        # Set the username directly - don't rely on saved state
        self.current_chat_user = username
        self.current_chat_user_id = username
        self.current_room_id = room_id
        
        print(f"Loading messages for direct chat room: {room_id}, user: {self.current_chat_user}")
        
        try:
            # Direct bitwise comparison for token validation
            if (auth_token == "") | (auth_token == None):
                print("Auth token is empty or None")
                self.room_error_message = "Authentication token missing"
                self.is_loading = False
                return
            
            async with httpx.AsyncClient() as client:
                # Using the messages endpoint with room_id as query parameter
                response = await client.get(
                    f"http://startup-hub:8000/api/communication/rooms/{room_id}/messages",
                    headers={"Authorization": f"Token {auth_token}"}
                )
                
                if response.status_code == 200:
                    messages = response.json()
                    current_username = AuthState.username
                    
                    # Convert API messages format to chat_history format
                    for msg in messages:
                        sender_type = "user" if msg["sender"]["username"] == current_username else "other"
                        content = msg["content"]
                        
                        # Handle different message types
                        if msg["message_type"] != "text":
                            if msg["image"]:
                                content = msg["image"]
                            elif msg["video"]:
                                content = msg["video"]
                            elif msg["audio"]:
                                content = msg["audio"]
                            elif msg["document"]:
                                content = msg["document"]
                                
                        self.chat_history.append((sender_type, content))
                else:
                    self.room_error_message = f"Failed to load messages: {response.status_code} {response.text}"
        except Exception as e:
            self.room_error_message = f"Error loading messages: {str(e)}"
        finally:
            self.is_loading = False
            # Reaffirm the username one more time just to be safe
            self.current_chat_user = username
    
    async def load_room_messages(self, room_id: str):
        """Load messages for a specific room"""
        # Save the current chat user before resetting state
        current_user = self.current_chat_user
        
        self.reset_state(preserve_username=False)
        self.is_loading = True
        auth_token = AuthState.token
        
        # Restore the current chat user after reset
        self.current_chat_user = current_user
        self.current_room_id = room_id
        
        print(f"Loading messages for room: {room_id}, user: {self.current_chat_user}")
        
        try:
            # Direct bitwise comparison for token validation
            if (auth_token == "") | (auth_token == None):
                print("Auth token is empty or None")
                self.room_error_message = "Authentication token missing"
                self.is_loading = False
                return
            
            async with httpx.AsyncClient() as client:
                # First get room details to get the name
                room_response = await client.get(
                    f"http://startup-hub:8000/api/communication/rooms/{room_id}/",
                    headers={"Authorization": f"Token {auth_token}"}
                )
                
                if room_response.status_code == 200:
                    room_data = room_response.json()
                    # Update room name
                    self.current_chat_user = room_data.get("name", self.current_chat_user)
                
                # Using the messages endpoint with room_id as query parameter
                response = await client.get(
                    f"http://startup-hub:8000/api/communication/messages/?room_id={room_id}",
                    headers={"Authorization": f"Token {auth_token}"}
                )
                
                if response.status_code == 200:
                    messages = response.json()
                    current_username = AuthState.username
                    
                    # Convert API messages format to chat_history format
                    for msg in messages:
                        sender_type = "user" if msg["sender"]["username"] == current_username else "other"
                        content = msg["content"]
                        
                        # Handle different message types
                        if msg["message_type"] != "text":
                            if msg["image"]:
                                content = msg["image"]
                            elif msg["video"]:
                                content = msg["video"]
                            elif msg["audio"]:
                                content = msg["audio"]
                            elif msg["document"]:
                                content = msg["document"]
                                
                        self.chat_history.append((sender_type, content))
                else:
                    self.room_error_message = f"Failed to load messages: {response.status_code} {response.text}"
        except Exception as e:
            self.room_error_message = f"Error loading messages: {str(e)}"
        finally:
            self.is_loading = False
    
    @rx.event
    async def create_direct_chat(self, username: str):
        """Create a direct message chat with a user"""
        try:
            auth_token = AuthState.token
            
            # Direct token validation
            if (auth_token == "") | (auth_token == None):
                self.room_error_message = "Authentication token missing"
                return
            
            async with httpx.AsyncClient() as client:
                # Use the create_direct_message endpoint
                response = await client.post(
                    "http://startup-hub:8000/api/communication/rooms/create_direct_message/",
                    headers={"Authorization": f"Token {auth_token}"},
                    json={
                        "username": username
                    }
                )
                
                if response.status_code in (200, 201):
                    room_data = response.json()
                    # Reload rooms to get the new room
                    await self.load_rooms()
                    # Yield the redirect instead of returning it
                    yield rx.redirect(f"/chat/user/{username}")
                else:
                    raise ValueError(f"Failed to create direct chat: {response.status_code} {response.text}")
        except Exception as e:
            self.room_error_message = f"Error creating direct chat: {str(e)}"

    @rx.event
    async def create_group_chat(self, name: str, max_participants: int = 10, participants: List[str] = None):
        """Create a new group chat room"""
        try:
            auth_token = AuthState.token
            
            # Direct token validation
            if (auth_token == "") | (auth_token == None):
                self.room_error_message = "Authentication token missing"
                return
            
            if participants is None or len(participants) == 0:
                raise ValueError("No participants selected for group chat")
            
            async with httpx.AsyncClient() as client:
                # Use the rooms endpoint to create a new group chat
                response = await client.post(
                    "http://startup-hub:8000/api/communication/rooms/",
                    headers={"Authorization": f"Token {auth_token}"},
                    json={
                        "name": name,
                        "room_type": "group",
                        "max_participants": max_participants,
                        "participants": participants
                    }
                )
                
                if response.status_code in (200, 201):
                    room_data = response.json()
                    # Reload rooms to get the new room
                    await self.load_rooms()
                    # Yield the redirect instead of returning it
                    yield rx.redirect(f"/chat/room/{room_data['id']}")
                else:
                    raise ValueError(f"Failed to create group chat: {response.status_code} {response.text}")
        except Exception as e:
            self.room_error_message = f"Error creating group chat: {str(e)}"

    @rx.event
    def handle_key_down(self, key_event):
        """Handle key down events on the input field
        The key_event is the raw keyboard event from the frontend
        """
        # Check if the key is Enter
        if key_event == "Enter":
            return self.send_message()
        return None

    @rx.event
    async def handle_route_change(self, route: str):
        """Handle route changes to reload the chat data."""
        print(f"Route changed to: {route}")
        await self.initialize_chat()
        return

    @rx.event
    async def setup_room_chat(self):
        """Set up room chat from URL parameters"""
        try:
            # Get the room_id parameter directly from the router's page params
            room_id = None
            if hasattr(self, "router") and hasattr(self.router, "page"):
                page = self.router.page
                if hasattr(page, "params"):
                    params = page.params
                    if isinstance(params, dict):
                        room_id = params.get("room_id")
                    else:
                        # Handle case where params is not a dict
                        for key, value in params:
                            if key == "room_id":
                                room_id = value
                                break
            
            print(f"Room chat setup - room_id: {room_id}")
            
            if not room_id:
                print("No room_id found in URL parameters")
                self.room_error_message = "No room ID found in URL"
                yield
                return
            
            # Update the current room ID and type
            self.current_room_id = str(room_id)
            self.current_room_type = "group"
            
            # Reset the state but preserve room ID
            self.reset_state(preserve_username=False)
            self.current_room_id = str(room_id)
            
            # Set a default room name (we'll try to update it in load_room_messages)
            self.current_chat_user = f"Group Chat"
            
            # Load the room messages
            print(f"Loading messages for room ID: {self.current_room_id}")
            await self.load_room_messages(str(room_id))
            
            print(f"Room chat setup complete for room: {room_id}")
            yield
        except Exception as e:
            print(f"Error in setup_room_chat: {str(e)}")
            self.room_error_message = f"Error setting up room chat: {str(e)}"
            yield
    
    @rx.event
    async def setup_direct_chat(self):
        """Set up direct chat from URL parameters"""
        try:
            # Get the chat_user parameter directly from the router's page params
            chat_user = None
            if hasattr(self, "router") and hasattr(self.router, "page"):
                page = self.router.page
                if hasattr(page, "params"):
                    params = page.params
                    if isinstance(params, dict):
                        chat_user = params.get("chat_user")
                    else:
                        # Handle case where params is not a dict
                        for key, value in params:
                            if key == "chat_user":
                                chat_user = value
                                break
            
            print(f"Direct chat setup - chat_user: {chat_user}")
            
            if not chat_user:
                print("No chat_user found in URL parameters")
                self.room_error_message = "No chat user found in URL"
                yield
                return
            
            # Reset the state
            self.reset_state(preserve_username=False)
            
            # Explicitly set the current chat user
            self.current_chat_user = str(chat_user)
            self.current_chat_user_id = str(chat_user)
            self.current_room_type = "direct"
            
            # Debug output
            print(f"DIRECT CHAT DEBUG - User set to: {self.current_chat_user}")
            
            # Directly call the async load method
            await self.load_direct_chat_messages(str(chat_user))
            
            print(f"Direct chat setup complete for user: {chat_user}")
            yield
        except Exception as e:
            print(f"Error in setup_direct_chat: {str(e)}")
            self.room_error_message = f"Error setting up direct chat: {str(e)}"
            yield

    @rx.event
    async def load_messages_event(self, identifier: str, chat_type: str):
        """Event wrapper to load messages based on chat type"""
        if chat_type == "direct":
            await self.load_direct_chat_messages(identifier)
        else:
            await self.load_room_messages(identifier)
            
    @rx.event
    async def initiate_call(self, is_video: bool = False):
        """Start a call in the current room via API"""
        try:
            auth_token = AuthState.token
            
            # Direct token validation
            if (auth_token == "") | (auth_token == None):
                self.room_error_message = "Authentication token missing"
                return
            
            room_id = self.current_room_id
            if not room_id:
                raise ValueError("Cannot start call: Room not found")
            
            async with httpx.AsyncClient() as client:
                # Use the start_call endpoint
                response = await client.post(
                    f"http://startup-hub:8000/api/communication/rooms/{room_id}/start_call/",
                    headers={"Authorization": f"Token {auth_token}"},
                    json={
                        "is_video": is_video
                    }
                )
                
                if response.status_code in (200, 201):
                    call_data = response.json()
                    # Handle call UI display
                    if is_video:
                        await self.video_call()
                    else:
                        await self.audio_call()
                else:
                    raise ValueError(f"Failed to start call: {response.status_code} {response.text}")
        except Exception as e:
            self.room_error_message = f"Error starting call: {str(e)}"

def create_group_modal() -> rx.Component:
    """Modal for creating a new group chat."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("plus"),
                variant="ghost",
                color="white",
                size="1",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Create New Group Chat"),
            rx.dialog.description(
                rx.vstack(
                    rx.input(
                        placeholder="Group Name",
                        value=ChatRoomState.group_name,
                        on_change=ChatRoomState.set_group_name,
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Max Participants (default: 10)",
                        type_="number",
                        value=str(ChatRoomState.max_participants),
                        on_change=ChatRoomState.set_max_participants,
                        width="100%",
                    ),
                    rx.divider(),
                    rx.text("Select Participants:", font_weight="bold"),
                    rx.cond(
                        len(ChatRoomState.rooms_data) > 0,
                        rx.vstack(
                            rx.foreach(
                                ChatRoomState.rooms_data,
                                lambda room: rx.cond(
                                    room.room_type == "direct",
                                    rx.hstack(
                                        rx.avatar(
                                            name=room.name,
                                            size="3",
                                        ),
                                        rx.text(room.name),
                                        # Checkbox for selecting participants
                                        rx.checkbox(
                                            on_change=lambda checked, name=room.name: ChatRoomState.toggle_participant(name),
                                        ),
                                    ),
                                    rx.box()  # Empty box for non-direct chats
                                )
                            ),
                        ),
                        rx.text("No users available to add", color="gray.500"),
                    ),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button(
                                "Cancel",
                                variant="outline",
                            ),
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Create Group",
                                on_click=lambda: ChatRoomState.create_group_chat(
                                    ChatRoomState.group_name, 
                                    ChatRoomState.max_participants,
                                    ChatRoomState.selected_participants
                                ),
                                is_disabled=rx.cond(
                                    (ChatRoomState.group_name == "") | (len(ChatRoomState.selected_participants) == 0),
                                    True,
                                    False,
                                ),
                            ),
                        ),
                        justify="between",
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
            ),
            bg="#2a2a2a",
            color="white",
            border_radius="md",
            padding="15px",
            width="90%",
            max_width="500px",
        ),
        open=ChatRoomState.show_create_group_modal,
        on_open_change=ChatRoomState.toggle_create_group_modal,
    )

def room_list() -> rx.Component:
    """Display a list of available chat rooms."""
    return rx.vstack(
        rx.hstack(
            rx.heading("Chat Rooms", size="3", color="white"),
            rx.spacer(),
            create_group_modal(),  # Now this has its own button in the dialog trigger
            width="100%",
            padding="10px",
        ),
        rx.cond(
            ChatRoomState.is_loading,
            rx.spinner(),
            rx.cond(
                len(ChatRoomState.rooms_data) > 0,
                rx.vstack(
                    rx.foreach(
                        ChatRoomState.rooms_data,
                        lambda room: rx.hstack(
                            rx.avatar(
                                name=room.name,
                                size="5",
                                border="2px solid white",
                                margin_right="10px",
                            ),
                            rx.vstack(
                                rx.text(
                                    room.name, 
                                    font_weight="bold", 
                                    color="white"
                                ),
                                rx.text(
                                    rx.cond(
                                        room.last_message != None,
                                        rx.cond(
                                            room.last_message.content != "",
                                            room.last_message.content,
                                            "Media message"
                                        ),
                                        "No messages yet"
                                    ),
                                    color="gray.300",
                                    font_size="sm",
                                    css={"textOverflow": "ellipsis", "overflow": "hidden", "whiteSpace": "nowrap", "maxWidth": "150px"}
                                ),
                                align_items="start",
                                spacing="0",
                            ),
                            spacing="4",
                            padding="10px",
                            border_radius="md",
                            width="100%",
                            _hover={"bg": "rgba(255, 255, 255, 0.1)"},
                            cursor="pointer",
                            transition="all 0.2s ease-in-out",
                            on_click=rx.redirect(f"/chat/room/{room.id}"),
                        ),
                    ),
                    overflow="auto",
                    height="100%",
                    width="100%",
                    spacing="1",
                ),
                rx.vstack(
                    rx.icon("mail", color="gray.400", font_size="4xl"),
                    rx.text("No chat rooms available", color="gray.400"),
                    rx.text(
                        "Connect with others to start chatting",
                        color="gray.500",
                        font_size="sm",
                    ),
                    justify="center",
                    align="center",
                    height="100%",
                    spacing="4",
                ),
            ),
        ),
        height="100%",
        width="250px",
        bg="#1e1e1e",
        border_right="1px solid #333",
        overflow="auto",
    )

@rx.page
def chatroom_page():
    """Main chat room page that integrates the room list and chat interface."""
    return rx.vstack(
        rx.heading("Chat Room", size="3", color="white"),
        rx.text("This is a minimal chat page to help diagnose issues", color="white"),
        rx.button(
            "Refresh",
            on_click=ChatRoomState.load_rooms,
            color_scheme="blue",
        ),
        rx.cond(
            ChatRoomState.room_error_message != "",
            rx.box(
                rx.hstack(
                    rx.icon("warning", color="red"),
                    rx.text(ChatRoomState.room_error_message, color="white"),
                ),
                bg="rgba(255, 0, 0, 0.2)",
                padding="10px",
                border_radius="md",
            ),
            rx.fragment(),
        ),
        padding="20px",
        spacing="4",
        bg="#2d2d2d",
        width="100%",
        height="100vh",
    )

@rx.page(route="/chat/room/[room_id]")
def chat_room_route():
    """Route for /chat/room/{room_id}"""
    return rx.box(
        rx.hstack(
            sidebar(),
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
        # WebRTC call components
        webrtc_calling_popup(),
        webrtc_call_popup(),
        webrtc_video_call_popup(),
        incoming_call_popup(),
        on_mount=ChatRoomState.setup_room_chat,
    )

@rx.page(route="/chat/user/[chat_user]")
def direct_chat_route():
    """Route for /chat/user/{chat_user}"""
    return rx.box(
        rx.hstack(
            sidebar(),
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
        # WebRTC call components
        webrtc_calling_popup(),
        webrtc_call_popup(),
        webrtc_video_call_popup(),
        incoming_call_popup(),
        on_mount=ChatRoomState.setup_direct_chat,
    )

# Define the UI components from Chat_Page.py

def sidebar() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Startup HUB", size="3", color="white"),
            rx.spacer(),
            width="100%",
            padding="10px",
        ),
        rx.vstack(
            rx.hstack(
                rx.icon("message-square", color="white", font_size="18px"),
                rx.text("Chat", color="white", font_size="16px"),
                width="100%",
                padding="10px",
                bg="rgba(255, 255, 255, 0.1)",  # Active item
                border_radius="md",
            ),
            rx.hstack(
                rx.icon("users", color="white", font_size="18px"),
                rx.text("Contacts", color="white", font_size="16px"),
                width="100%",
                padding="10px",
                _hover={"bg": "rgba(255, 255, 255, 0.1)"},
                border_radius="md",
                cursor="pointer",
            ),
            rx.hstack(
                rx.icon("phone", color="white", font_size="18px"),
                rx.text("Calls", color="white", font_size="16px"),
                width="100%",
                padding="10px",
                _hover={"bg": "rgba(255, 255, 255, 0.1)"},
                border_radius="md",
                cursor="pointer",
            ),
            rx.hstack(
                rx.icon("settings", color="white", font_size="18px"),
                rx.text("Settings", color="white", font_size="16px"),
                width="100%",
                padding="10px",
                _hover={"bg": "rgba(255, 255, 255, 0.1)"},
                border_radius="md",
                cursor="pointer",
            ),
            width="100%",
            spacing="2",
            align_items="start",
        ),
        rx.spacer(),
        rx.hstack(
            rx.avatar(name="User", size="2"),
            rx.text("Your Profile", color="white", font_size="14px"),
            width="100%",
            padding="10px",
            _hover={"bg": "rgba(255, 255, 255, 0.1)"},
            border_radius="md",
            cursor="pointer",
        ),
        height="100vh",
        width="200px",
        bg="#1e1e1e",
        border_right="1px solid #444",
        padding="10px",
    )

def user_header() -> rx.Component:
    return rx.hstack(
        rx.avatar(name=ChatState.current_chat_user, size="2", border="2px solid white"),
        rx.text(ChatState.current_chat_user, font_weight="bold", color="white", font_size="16px"),
        rx.spacer(),
        rx.hstack(
            # Audio call button
            rx.button(
                rx.icon("phone", color="white", font_size="18px"),
                on_click=ChatRoomState.room_audio_call,
                variant="ghost",
                _hover={
                    "bg": "rgba(255, 255, 255, 0.1)",
                    "transform": "scale(1.2)",
                },
                transition="all 0.2s ease-in-out",
            ),
            # Video call button
            rx.button(
                rx.icon("video", color="white", font_size="18px"),
                on_click=ChatRoomState.room_video_call,
                variant="ghost",
                _hover={
                    "bg": "rgba(255, 255, 255, 0.1)",
                    "transform": "scale(1.2)",
                },
                transition="all 0.2s ease-in-out",
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
    is_upload = isinstance(message, str) and message.startswith("/_upload")
    
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
                    src=message,
                    max_width="200px",
                    border_radius="15px"
                ),
                rx.text(message, color="#333333")
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

def chat() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.foreach(
                ChatState.chat_history,
                lambda messages: message_display(messages[0], messages[1])
            ),
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
    return rx.hstack(
        rx.hstack(
            rx.input(
                value=ChatState.message,
                placeholder="Type a message...",
                on_change=ChatState.set_message,
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
    """The original chat page from Chat_Page.py"""
    return rx.box(
        rx.hstack(
            sidebar(),
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
        # WebRTC call components
        webrtc_calling_popup(),
        webrtc_call_popup(),
        webrtc_video_call_popup(),
        incoming_call_popup(),
    )

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