import reflex as rx
from ..Matcher.SideBar import sidebar
class ChatState(rx.State):
    pass

def chat_display() -> rx.Component:
    return rx.box(
        rx.text("Chat Display"),
    )

def chat_page() -> rx.Component:
    return rx.box(
        rx.center(
            rx.vstack(
                chat_display(),
            ),
        ),
    )



