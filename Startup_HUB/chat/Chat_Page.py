import reflex as rx
from ..Matcher.SideBar import sidebar

class ChatState(rx.State):
    # Initialize with type annotation as required
    chat_history: list[tuple[str, str]] = [
        ("other", "Hello there!"),
        ("user", "Hi, how are you?"),
        ("other", "I'm doing great, thanks for asking!"),
    ]
    message: str = ""
    current_chat_user: str = "Andy Collins"

    @rx.event
    async def send_message(self):
        if self.message.strip():
            self.chat_history.append(("user", self.message))
            self.message = ""
            yield

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

def user_header() -> rx.Component:
    return rx.hstack(
        rx.avatar(name="Andy Collins", size="2", border="2px solid white"),
        rx.text(ChatState.current_chat_user, font_weight="bold", color="white", font_size="16px"),
        rx.spacer(),
        rx.hstack(
            rx.icon("phone", color="white", font_size="18px"),
            rx.icon("video", color="white", font_size="18px"),
            rx.icon("info", color="white", font_size="18px"),
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
            rx.upload(
                rx.button(
                    rx.icon("paperclip", color="#AAAAAA", font_size="18px"),
                    variant="ghost",
                    padding="0",
                    margin_right="5px",
                    cursor="pointer",
                    _hover={"color": "#80d0ea"},
                    transition="all 0.2s ease-in-out",
                ),
                id="file-upload",
                accept={
                    "image/png": [".png"],
                    "image/jpeg": [".jpg", ".jpeg"],
                    "image/gif": [".gif"]
                },
                on_drop=ChatState.handle_upload,
                multiple=True,
                height="40px",
                display="inline-flex",
                align_items="center",
            ),
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
        )
    )
