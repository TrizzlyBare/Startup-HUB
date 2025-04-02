import reflex as rx
from .webrtc_state import WebRTCState

def calling_popup() -> rx.Component:
    """Display a popup when initiating a call."""
    return rx.cond(
        WebRTCState.is_call_initiator & ~WebRTCState.is_in_call,
        rx.box(
            rx.vstack(
                rx.text("Calling...", font_size="1.5em", font_weight="bold"),
                rx.spinner(size="3", margin_y="4"),
                rx.button(
                    "Cancel",
                    on_click=WebRTCState.leave_call,
                ),
                spacing="4",
                padding="4",
                bg="white",
                border="1px solid",
                border_color="gray.100",
            ),
            position="fixed",
            top="50%",
            left="50%",
            transform="translate(-50%, -50%)",
            z_index="1000",
        ),
    )

def call_popup() -> rx.Component:
    """Display a popup for audio calls."""
    return rx.cond(
        WebRTCState.is_in_call & ~WebRTCState.is_video_enabled,
        rx.box(
            rx.vstack(
                rx.heading("Audio Call", size="3"),
                call_controls(),
                padding="4",
                bg="white",
                border="1px solid",
                border_color="gray.100",
                width="400px",
            ),
            position="fixed",
            top="50%",
            left="50%",
            transform="translate(-50%, -50%)",
            z_index="1000",
        ),
    )

def video_call_popup() -> rx.Component:
    """Display a popup for video calls."""
    return rx.cond(
        WebRTCState.is_in_call & WebRTCState.is_video_enabled,
        rx.box(
            rx.vstack(
                rx.heading("Video Call", size="3"),
                rx.box(
                    rx.html("<video id='local-video' autoplay playsinline muted></video>"),
                    position="relative",
                    width="320px",
                    height="240px",
                    overflow="hidden",
                    bg="black",
                ),
                call_controls(),
                padding="4",
                bg="white",
                border="1px solid",
                border_color="gray.100",
                max_width="800px",
                width="90vw",
            ),
            position="fixed",
            top="50%",
            left="50%",
            transform="translate(-50%, -50%)",
            z_index="1000",
        ),
    )

def group_call_popup() -> rx.Component:
    """Display a popup for group video calls."""
    return rx.fragment()  # Simplified version

def incoming_call_popup() -> rx.Component:
    """Display a popup for incoming calls."""
    return rx.cond(
        ~WebRTCState.is_call_initiator & ~WebRTCState.is_in_call,
        rx.box(
            rx.vstack(
                rx.heading("Incoming Call", size="3"),
                rx.text("Incoming call", font_size="1.2em"),
                rx.hstack(
                    rx.button(
                        "Accept",
                        on_click=WebRTCState.accept_call,
                    ),
                    rx.button(
                        "Decline",
                        on_click=WebRTCState.leave_call,
                    ),
                    spacing="4",
                ),
                padding="4",
                bg="white",
                border="1px solid",
                border_color="gray.100",
            ),
            position="fixed",
            top="50%",
            left="50%",
            transform="translate(-50%, -50%)",
            z_index="1000",
        ),
    )

def call_controls() -> rx.Component:
    """Call control buttons."""
    return rx.hstack(
        rx.button(
            "Mute",
            on_click=WebRTCState.toggle_audio,
        ),
        rx.button(
            "Video",
            on_click=WebRTCState.toggle_video,
        ),
        rx.button(
            "End Call",
            on_click=WebRTCState.leave_call,
        ),
        spacing="4",
    ) 