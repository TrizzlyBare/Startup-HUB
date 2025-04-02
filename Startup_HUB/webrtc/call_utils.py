import reflex as rx
from typing import Any, Dict, List, Optional
from .webrtc_state import WebRTCState

def start_audio_call(user_id: str, username: str) -> rx.event.EventHandler:
    """Start an audio call with a specific user.
    
    Args:
        user_id: ID of the user to call
        username: Username of the user to call
    
    Returns:
        Event handler to initiate the call
    """
    async def start_call_event(state: WebRTCState):
        # Start a call with the specified user
        state.start_call(user_id, is_video=False)
        
        # Add the user as a participant
        state.add_participant(user_id, username)
        
        # Initialize WebRTC and connect to signaling server
        await state.initialize_webrtc()
        await state.connect_to_signaling_server()
    
    return start_call_event

def start_video_call(user_id: str, username: str) -> rx.event.EventHandler:
    """Start a video call with a specific user.
    
    Args:
        user_id: ID of the user to call
        username: Username of the user to call
    
    Returns:
        Event handler to initiate the call
    """
    async def start_call_event(state: WebRTCState):
        # Start a video call with the specified user
        state.start_call(user_id, is_video=True)
        
        # Add the user as a participant
        state.add_participant(user_id, username)
        
        # Initialize WebRTC and connect to signaling server
        await state.initialize_webrtc()
        await state.connect_to_signaling_server()
    
    return start_call_event

def answer_call() -> rx.event.EventHandler:
    """Answer an incoming call.
    
    Returns:
        Event handler to answer the call
    """
    async def answer_call_event(state: WebRTCState):
        # Set the call as active
        state.is_in_call = True
        
        # Initialize WebRTC if not already done
        await state.initialize_webrtc()
        await state.connect_to_signaling_server()
    
    return answer_call_event

def decline_call() -> rx.event.EventHandler:
    """Decline an incoming call.
    
    Returns:
        Event handler to decline the call
    """
    async def decline_call_event(state: WebRTCState):
        # Decline the call by leaving it
        await state.leave_call()
    
    return decline_call_event

def end_call() -> rx.event.EventHandler:
    """End the current call.
    
    Returns:
        Event handler to end the call
    """
    async def end_call_event(state: WebRTCState):
        # End the call
        await state.leave_call()
    
    return end_call_event

def toggle_audio() -> rx.event.EventHandler:
    """Toggle audio on/off.
    
    Returns:
        Event handler to toggle audio
    """
    async def toggle_audio_event(state: WebRTCState):
        # Toggle audio
        await state.toggle_audio()
    
    return toggle_audio_event

def toggle_video() -> rx.event.EventHandler:
    """Toggle video on/off.
    
    Returns:
        Event handler to toggle video
    """
    async def toggle_video_event(state: WebRTCState):
        # Toggle video
        await state.toggle_video()
    
    return toggle_video_event

def create_call_button(user_id: str, username: str, is_video: bool = False) -> rx.Component:
    """Create a call button for a specific user.
    
    Args:
        user_id: ID of the user to call
        username: Username of the user to call
        is_video: Whether to start a video call (True) or audio call (False)
    
    Returns:
        Call button component
    """
    icon = "video" if is_video else "phone"
    tooltip = "Video Call" if is_video else "Audio Call"
    event_handler = start_video_call(user_id, username) if is_video else start_audio_call(user_id, username)
    
    return rx.tooltip(
        rx.button(
            rx.icon(icon),
            on_click=event_handler,
            variant="outline",
            color_scheme="blue",
            border_radius="full",
            size="sm",
        ),
        label=tooltip,
    ) 