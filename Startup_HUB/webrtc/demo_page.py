import reflex as rx
from . import WebRTCState
from .webrtc_components import (
    calling_popup,
    call_popup,
    video_call_popup,
    group_call_popup,
    incoming_call_popup,
    call_controls
)
from .call_utils import (
    start_audio_call,
    start_video_call,
    answer_call,
    decline_call,
    end_call,
    toggle_audio,
    toggle_video
)

class WebRTCDemoState(rx.State):
    """State for the WebRTC demo page."""
    
    user_id: str = "demo_user"
    username: str = "Demo User"
    peer_id: str = "peer_user"
    peer_name: str = "Test User"

def demo_page() -> rx.Component:
    """Demo page to test WebRTC functionality."""
    return rx.box(
        rx.vstack(
            rx.heading("WebRTC Demo", size="3", margin_bottom="4"),
            
            # User info
            rx.form(
                rx.vstack(
                    rx.hstack(
                        rx.text("Your User ID:"),
                        rx.input(
                            value=WebRTCDemoState.user_id,
                            on_change=WebRTCDemoState.set_user_id,
                            placeholder="Your User ID",
                            width="100%",
                        ),
                    ),
                    rx.hstack(
                        rx.text("Your Username:"),
                        rx.input(
                            value=WebRTCDemoState.username,
                            on_change=WebRTCDemoState.set_username,
                            placeholder="Your Username",
                            width="100%",
                        ),
                    ),
                    rx.hstack(
                        rx.text("Peer User ID:"),
                        rx.input(
                            value=WebRTCDemoState.peer_id,
                            on_change=WebRTCDemoState.set_peer_id,
                            placeholder="Peer User ID",
                            width="100%",
                        ),
                    ),
                    rx.hstack(
                        rx.text("Peer Username:"),
                        rx.input(
                            value=WebRTCDemoState.peer_name,
                            on_change=WebRTCDemoState.set_peer_name,
                            placeholder="Peer Username",
                            width="100%",
                        ),
                    ),
                    spacing="4",
                ),
            ),
            
            # Call controls
            rx.box(
                rx.heading("Call Controls", size="4", margin_y="4"),
                rx.hstack(
                    rx.button(
                        "Start Audio Call",
                        on_click=start_audio_call(WebRTCDemoState.peer_id, WebRTCDemoState.peer_name),
                        color_scheme="blue",
                    ),
                    rx.button(
                        "Start Video Call",
                        on_click=start_video_call(WebRTCDemoState.peer_id, WebRTCDemoState.peer_name),
                        color_scheme="green",
                    ),
                    spacing="4",
                ),
                padding="4",
                border="1px solid",
                border_color="gray.200",
                border_radius="md",
                margin_bottom="4",
            ),
            
            # Media controls
            rx.box(
                rx.heading("Media Controls", size="4", margin_y="4"),
                rx.hstack(
                    rx.button(
                        "Toggle Audio",
                        on_click=toggle_audio(),
                        color_scheme="blue",
                    ),
                    rx.button(
                        "Toggle Video",
                        on_click=toggle_video(),
                        color_scheme="purple",
                    ),
                    rx.button(
                        "End Call",
                        on_click=end_call(),
                        color_scheme="red",
                    ),
                    spacing="4",
                ),
                padding="4",
                border="1px solid",
                border_color="gray.200",
                border_radius="md",
                margin_bottom="4",
            ),
            
            # Call status
            rx.box(
                rx.heading("Call Status", size="4", margin_y="4"),
                rx.vstack(
                    rx.text("In Call: ", WebRTCState.is_in_call),
                    rx.text("Audio Enabled: ", WebRTCState.is_audio_enabled),
                    rx.text("Video Enabled: ", WebRTCState.is_video_enabled),
                    rx.text("Participants: ", rx.foreach(
                        WebRTCState.call_participants,
                        lambda participant: rx.text(participant.get("username", "Unknown"))
                    )),
                    align_items="start",
                    spacing="2",
                ),
                padding="4",
                border="1px solid",
                border_color="gray.200",
                border_radius="md",
            ),
            
            padding="8",
            max_width="800px",
            width="100%",
            margin="0 auto",
        ),
        
        # Call popups
        calling_popup(),
        call_popup(),
        video_call_popup(),
        group_call_popup(),
        incoming_call_popup(),
    ) 