import reflex as rx
from typing import List, Dict, Any, TypedDict, Optional
import httpx
from ..Auth.AuthPage import AuthState

def matches_content() -> rx.Component:
    """Content for the Matches tab."""
    from .Matcher_Page import MatchState
    return rx.vstack(
        rx.foreach(
            MatchState.matches,
            lambda match: rx.hstack(
                rx.avatar(
                    src=rx.cond(
                        match["matched_user_details"]["profile_picture_url"] != None,
                        match["matched_user_details"]["profile_picture_url"],
                        "/profile.jpg"
                    ),
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text(
                        rx.cond(
                            (match["matched_user_details"]["first_name"] != "") & 
                            (match["matched_user_details"]["last_name"] != ""),
                            f"{match['matched_user_details']['first_name']} {match['matched_user_details']['last_name']}",
                            match["matched_user"]
                        ),
                        font_weight="bold",
                        class_name="text-black"
                    ),
                    rx.text(
                        rx.cond(
                            match["matched_user_details"]["industry"] != "",
                            match["matched_user_details"]["industry"],
                            "No industry specified"
                        ),
                        class_name="text-gray-600"
                    ),
                    align_items="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("message-circle"),
                    on_click=lambda username=match["matched_user"]: MatchState.open_chat(username),
                    class_name="bg-blue-500 text-white p-2 rounded-full hover:bg-blue-600",
                    size="1",
                    tooltip="Chat with this user",
                ),
                spacing="4",
                class_name="w-full p-2 hover:bg-gray-100 rounded-lg cursor-pointer",
                on_click=lambda username=match["matched_user"]: MatchState.open_chat(username),
            ),
        ),
        align_items="stretch",
        padding_x="4",
        spacing="3",
    )

def liked_content() -> rx.Component:
    """Content for the Liked tab."""
    from .Matcher_Page import MatchState
    return rx.vstack(
        rx.foreach(
            MatchState.likes,
            lambda like: rx.hstack(
                rx.avatar(
                    src=rx.cond(
                        like["liked_user_details"]["profile_picture_url"] is not None,
                        like["liked_user_details"]["profile_picture_url"],
                        "../../profile.jpg"
                    ),
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text(
                        rx.cond(
                            (like["liked_user_details"]["first_name"] != "") & 
                            (like["liked_user_details"]["last_name"] != ""),
                            f"{like['liked_user_details']['first_name']} {like['liked_user_details']['last_name']}",
                            like["liked_user"]
                        ),
                        font_weight="bold",
                        class_name="text-black"
                    ),
                    rx.text(
                        rx.cond(
                            like["liked_user_details"]["industry"] is not None,
                            like["liked_user_details"]["industry"],
                            "No industry specified"
                        ),
                        class_name="text-gray-600"
                    ),
                    align_items="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("message-circle"),
                    on_click=lambda username=like["liked_user"]: MatchState.open_chat(username),
                    class_name="bg-blue-500 text-white p-2 rounded-full hover:bg-blue-600",
                    size="1",
                    tooltip="Chat with this user",
                ),
                spacing="4",
                class_name="w-full p-2 hover:bg-gray-100 rounded-lg cursor-pointer",
                on_click=lambda username=like["liked_user"]: MatchState.open_chat(username),
            ),
        ),
        align_items="stretch",
        padding_x="4",
        spacing="3",
    )

def messages_content() -> rx.Component:
    """Content for the Messages tab."""
    from .Matcher_Page import MatchState
    return rx.vstack(
        rx.cond(
            MatchState.rooms.length() > 0,
            rx.vstack(
                rx.foreach(
                    MatchState.rooms,
                    lambda room: rx.hstack(
                        rx.avatar(
                            src=rx.cond(
                                room["profile_image"] is not None,
                                room["profile_image"],
                                "../../profile.jpg"
                            ),
                            size="5",
                            class_name="rounded-full",
                        ),
                        rx.vstack(
                            rx.text(
                                room["name"],
                                font_weight="bold",
                                class_name="text-black"
                            ),
                            rx.text(
                                rx.cond(
                                    room["last_message"] is not None,
                                    rx.cond(
                                        room["last_message"]["content"] != "",
                                        room["last_message"]["content"],
                                        "Media message"
                                    ),
                                    "No messages yet"
                                ),
                                class_name="text-gray-600 truncate w-52",
                            ),
                            align_items="start",
                            width="full",
                        ),
                        spacing="4",
                        class_name="w-full p-2 hover:bg-gray-100 rounded-lg cursor-pointer",
                        on_click=lambda room_id=room["id"], room_name=room["name"], room_type=room["room_type"]: 
                            rx.cond(
                                room_type == "group",
                                MatchState.open_group_chat(room_id, room_name),
                                MatchState.open_chat(rx.cond(
                                    (room["participants"].length() > 1) & (room["participants"][0]["user"]["username"] == MatchState.get_username),
                                    room["participants"][1]["user"]["username"],
                                    room["participants"][0]["user"]["username"]
                                ))
                            ),
                    ),
                ),
                align_items="stretch",
                padding_x="4",
                spacing="3",
            ),
            rx.vstack(
                rx.image(
                    src="/empty-chat.svg",
                    width="200px",
                    height="200px",
                    opacity="0.5",
                ),
                rx.text(
                    "No messages yet", 
                    color="gray.500",
                    font_size="lg",
                ),
                rx.text(
                    "Start a conversation by clicking on a match or a liked user", 
                    color="gray.400",
                    font_size="sm",
                    text_align="center",
                ),
                justify="center",
                align_items="center",
                height="100%",
                spacing="4",
                padding="8",
            ),
        ),
        height="calc(100vh - 240px)",
        overflow_y="auto",
    )

def report_modal() -> rx.Component:
    """Report modal component."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.icon(
                "shield",
                color="black",
                class_name="w-10 h-10 bg-white rounded-full p-1 hover:bg-green-500 hover:text-white",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(
                "Report an Issue",
                class_name="text-3xl font-bold text-sky-600 text-center"
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        rx.select(
                            ["Inappropriate Content", "Technical Issue", "Harassment", "Other"],
                            placeholder="Select Issue Type",
                            name="issue_type",
                            required=True,
                        ),
                        rx.input(
                            placeholder="Enter username",
                            name="username",
                            required=True,
                            class_name="w-60 h-10 border rounded-xl bg-sky-600",
                        ),
                        rx.text_area(
                            placeholder="Describe the issue in detail...",
                            name="description",
                            required=True,
                            min_height="300px",
                            min_width = "550px",
                            class_name="bg-gray-600",
                        ),
                        rx.hstack(
                            rx.dialog.close(
                                rx.button(
                                    "Cancel",
                                    variant="soft",
                                    color_scheme="gray",
                                    class_name="bg-red-600 text-white hover:bg-red-700",
                                ),
                            ),
                            rx.button(
                                "Submit Report",
                                type="submit",
                                class_name="bg-green-600 text-white hover:bg-green-700",
                            ),
                            spacing="4",
                            justify="end",
                        ),
                        spacing="4",
                    ),
                    on_submit=lambda form_data: rx.window_alert(f"Report submitted: {form_data}"),
                    reset_on_submit=True,
                ),
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-xl",
        ),
    )

def create_group_modal() -> rx.Component:
    """Create new group chat modal component."""
    from .Matcher_Page import MatchState
    
    def handle_submit(form_data):
        """Handle form submission."""
        print(f"Form data received: {form_data}")
        print(f"Form data type: {type(form_data)}")
        
        # IMPORTANT: With Reflex, we must return an event chain, not process form data directly
        # Form processing happens in the create_direct_group_chat method instead
        
        # Return an event chain to avoid UntypedVarError
        return [
            # Pass the raw form_data Var to the method that knows how to handle it
            MatchState.create_direct_group_chat(form_data),
            # Show a success message
            rx.window_alert("Creating group chat..."),
        ]
        
    # Create the component with dialog
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.icon(
                "plus",
                color="black",
                class_name="w-8 h-8 bg-white rounded-full p-1 hover:bg-blue-500 hover:text-white",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(
                "Create New Group Chat",
                class_name="text-2xl font-bold text-sky-600 text-center font-mono"
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        rx.text(
                            "Group Name:",
                            class_name="font-semibold text-lg text-sky-300"
                        ),
                        rx.input(
                            name="group_name",
                            required=True,
                            class_name="w-full h-10 border rounded-xl bg-white text-black"
                        ),
                        rx.text(
                            "Max Members:",
                            class_name="font-semibold text-lg mt-4 text-sky-300"
                        ),
                        rx.input(
                            name="max_participants",
                            type="number",
                            min="2",
                            max="100",
                            default_value="10",
                            class_name="w-full h-10 border rounded-xl bg-white text-black",
                        ),
                        rx.text(
                            "Add Members",
                            class_name="font-semibold text-lg mt-4 text-sky-300",
                        ),
                        rx.vstack(
                            rx.foreach(
                                MatchState.likes,
                                lambda like: rx.hstack(
                                    rx.avatar(
                                        src=rx.cond(
                                            like["liked_user_details"]["profile_picture_url"] is not None,
                                            like["liked_user_details"]["profile_picture_url"],
                                            "../../profile.jpg"
                                        ),
                                        size="5",
                                        class_name="rounded-full",
                                    ),
                                    rx.text(
                                        rx.cond(
                                            (like["liked_user_details"]["first_name"] != "") & 
                                            (like["liked_user_details"]["last_name"] != ""),
                                            f"{like['liked_user_details']['first_name']} {like['liked_user_details']['last_name']}",
                                            like["liked_user"]
                                        ),
                                        class_name="text-black"
                                    ),
                                    rx.spacer(),
                                    # Use HTML input directly with data attribute
                                    rx.html(
                                        f"""
                                        <label class="flex items-center space-x-2 cursor-pointer">
                                            <input 
                                                type="checkbox" 
                                                name="member_{like['liked_user']}" 
                                                value="true"
                                                class="form-checkbox h-5 w-5 text-blue-600 rounded focus:ring-blue-500"
                                            />
                                            <span class="text-sm font-medium text-gray-700">Select</span>
                                        </label>
                                        """
                                    ),
                                    spacing="4",
                                    class_name="w-full p-2 hover:bg-gray-100 rounded-lg",
                                ),
                            ),
                            align_items="stretch",
                            spacing="2",
                            class_name="max-h-[300px] overflow-y-auto",
                        ),
                        rx.hstack(
                            rx.dialog.close(
                                rx.button(
                                    "Cancel",
                                    variant="soft",
                                    color_scheme="gray",
                                    class_name="bg-red-600 text-white hover:bg-red-700",
                                    type="button",
                                ),
                            ),
                            rx.button(
                                "Create Group",
                                type="submit",
                                class_name="bg-green-600 text-white hover:bg-green-700",
                            ),
                            spacing="4",
                            justify="end",
                        ),
                        spacing="4",
                    ),
                    on_submit=handle_submit,
                    reset_on_submit=True,
                ),
            ),
            max_width="500px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-xl",
        ),
    )

def sidebar(state=None) -> rx.Component:
    if state is None:
        from .Matcher_Page import MatchState
        active_state = MatchState
    else:
        active_state = state

    return rx.box(
        rx.vstack(
            # Top section with search and icons
            rx.hstack(
                rx.avatar(
                    src="../../profile.jpg",
                    size="5",
                    class_name="rounded-full object-cover border-4 border-white m-2",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.icon(
                        "search",
                        color="black",
                        class_name="w-10 h-10 bg-white rounded-full p-1 hover:bg-blue-500 hover:text-white cursor-pointer",
                        on_click=rx.redirect("/search"),
                    ),
                    report_modal(),
                    rx.icon(
                        "log-out",
                        color="black",
                        class_name="w-10 h-10 bg-white rounded-full p-1 hover:bg-red-500 hover:text-white cursor-pointer",
                        on_click=rx.redirect("/"),
                    ),
                    spacing="4",
                    class_name="m-4"
                ),
                width="full",
                padding="4",
                class_name="bg-sky-400",
            ),
            # Navigation tabs
            rx.hstack(
                rx.text(
                    "Matches",
                    color="black",
                    font_weight="bold",
                    cursor="pointer",
                    style={"fontSize": "18px"},
                    class_name=rx.cond(
                        getattr(active_state, "active_tab", "") == "Matches",
                        "border-b-2 border-sky-400",
                        ""
                    ),
                    on_click=lambda: active_state.set_active_tab("Matches") if hasattr(active_state, "set_active_tab") else rx.noop(),
                ),
                rx.text(
                    "Chat",
                    color="black",
                    font_weight="bold",
                    cursor="pointer",
                    style={"fontSize": "18px"},
                    class_name=rx.cond(
                        getattr(active_state, "active_tab", "") == "Liked",
                        "border-b-2 border-sky-400",
                        ""
                    ),
                    on_click=lambda: active_state.set_active_tab("Liked") if hasattr(active_state, "set_active_tab") else rx.noop(),
                ),
                rx.text(
                    "Group Chat",
                    color="black",
                    font_weight="bold",
                    cursor="pointer",
                    style={"fontSize": "18px"},
                    class_name=rx.cond(
                        getattr(active_state, "active_tab", "") == "Messages",
                        "border-b-2 border-sky-400",
                        ""
                    ),
                    on_click=lambda: active_state.set_active_tab("Messages") if hasattr(active_state, "set_active_tab") else rx.noop(),
                ),
                spacing="6",
                padding="4",
                class_name="ml-2"
            ),
            # Dynamic content based on active tab
            rx.cond(
                getattr(active_state, "active_tab", "") == "Matches",
                matches_content(),
                rx.cond(
                    getattr(active_state, "active_tab", "") == "Liked",
                    liked_content(),
                    messages_content(),
                ),
            ),
            # Create group button at bottom
            rx.cond(
                getattr(active_state, "active_tab", "") == "Messages",
                rx.hstack(
                    rx.spacer(),
                    create_group_modal(),
                    class_name="p-4",
                ),
                rx.spacer(),
            ),
            align_items="stretch",
            height="full",
        ),
        class_name="w-[350px] h-screen bg-sky-100 border-r border-gray-800",
    )