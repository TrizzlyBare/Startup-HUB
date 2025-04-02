import reflex as rx

class WebRTCState(rx.State):
    """State for managing WebRTC connections and calls."""
    
    # Call state
    is_in_call: bool = False
    is_call_initiator: bool = False
    is_audio_enabled: bool = True
    is_video_enabled: bool = False
    current_room_id: str = None
    connected_to_signaling: bool = False
    
    # Participant information
    call_participants: list = []
    remote_streams: dict = {}
    peer_connections: dict = {}
    
    # Signaling
    ice_servers = [
        {"urls": "stun:stun.l.google.com:19302"},
        {"urls": "stun:stun1.l.google.com:19302"},
        {"urls": "stun:stun2.l.google.com:19302"},
    ]
    
    def get_room_url(self) -> str:
        """Get the room ID for signaling."""
        if not self.current_room_id:
            return ""
        # Simple implementation - just return the room ID
        return self.current_room_id
    
    def start_call(self, user_id: str, is_video_enabled: bool):
        """Start a call with the given user.
        
        Args:
            user_id: The ID of the user to call.
            is_video_enabled: Whether to enable video for the call.
        """
        self.is_call_initiator = True
        self.is_in_call = False  # Will be set to True when the callee accepts
        self.is_video_enabled = is_video_enabled
        self.current_room_id = f"call_{user_id}"
        # After setting the room, connect to signaling
        self.connect_to_signaling_server()
    
    @rx.event
    async def accept_call(self):
        """Accept an incoming call."""
        self.is_in_call = True
        yield
    
    def add_participant(self, user_id: str, username: str):
        """Add a participant to the call."""
        # This will be handled by the JS code
        pass
    
    def remove_participant(self, user_id: str):
        """Remove a participant from the call."""
        # This will be handled by the JS code
        pass
    
    @rx.event
    async def initialize_webrtc(self):
        """Initialize WebRTC by calling the JavaScript function."""
        await rx.run_js("initializeWebRTC()")
        yield
    
    @rx.event
    async def connect_to_signaling_server(self):
        """Connect to the signaling server using JavaScript."""
        if not self.current_room_id or self.connected_to_signaling:
            return
        
        # Pass room ID to JS function
        await rx.run_js(f"connectToSignalingServer('{self.current_room_id}')")
        self.connected_to_signaling = True
        yield
    
    @rx.event
    async def toggle_audio(self):
        """Toggle audio on/off."""
        self.is_audio_enabled = not self.is_audio_enabled
        await rx.run_js(f"toggleAudio({str(self.is_audio_enabled).lower()})")
        yield
    
    @rx.event
    async def toggle_video(self):
        """Toggle video on/off."""
        self.is_video_enabled = not self.is_video_enabled
        await rx.run_js(f"toggleVideo({str(self.is_video_enabled).lower()})")
        yield
    
    @rx.event
    async def leave_call(self):
        """Leave the current call."""
        await rx.run_js("closeAllConnections()")
        self.is_in_call = False
        self.current_room_id = None
        self.connected_to_signaling = False
        self.call_participants = []
        self.remote_streams = {}
        self.peer_connections = {}
        yield 