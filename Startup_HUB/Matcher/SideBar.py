import reflex as rx

def matches_content() -> rx.Component:
    """Content for the Matches tab."""
    return rx.vstack(
        rx.text(
            "Potential Matches",
            font_weight="bold",
            class_name="text-xl mb-4",
        ),
        rx.vstack(
            rx.image(
                src="../../Soukaku.jpg",
                class_name="w-20 h-40 rounded-lg object-cover cursor-pointer hover:opacity-80 m-2 border-4 border-sky-400",
            ),
            rx.image(
                src="../../blue_cat.jpg",
                class_name="w-20 h-40 rounded-lg object-cover cursor-pointer hover:opacity-80 m-2 border-4 border-sky-400",
            ),
            rx.image(
                src="../../Jane_Doe.jpg",
                class_name="w-20 h-40 rounded-lg object-cover cursor-pointer hover:opacity-80 m-2 border-4 border-sky-400",
            ),
            align_items="start",
            padding_x="4",
            spacing="3",
        ),
        align_items="stretch",
    )

def liked_content() -> rx.Component:
    """Content for the Liked tab."""
    return rx.vstack(
        rx.text(
            "Liked Profiles",
            font_weight="bold",
            class_name="text-xl mb-4",
        ),
        rx.vstack(
            rx.image(
                src="../../profile.jpg",
                class_name="w-20 h-40 rounded-lg object-cover cursor-pointer hover:opacity-80 m-2 border-4 border-green-400",
            ),
            rx.image(
                src="../../Soukaku.jpg",
                class_name="w-20 h-40 rounded-lg object-cover cursor-pointer hover:opacity-80 m-2 border-4 border-green-400",
            ),
            align_items="start",
            padding_x="4",
            spacing="3",
        ),
        align_items="stretch",
    )

def messages_content() -> rx.Component:
    """Content for the Messages tab."""
    return rx.vstack(
        rx.text(
            "Messages",
            font_weight="bold",
            class_name="text-xl mb-4",
        ),
        rx.vstack(
            rx.hstack(
                rx.avatar(
                    src="../../profile.jpg",
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text("John Doe", font_weight="bold"),
                    rx.text("Hey, how are you?", class_name="text-gray-600"),
                    align_items="start",
                ),
                spacing="4",
                class_name="w-full p-2 hover:bg-gray-100 rounded-lg cursor-pointer",
            ),
            rx.hstack(
                rx.avatar(
                    src="../../Soukaku.jpg",
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text("Soukaku", font_weight="bold"),
                    rx.text("Let's connect!", class_name="text-gray-600"),
                    align_items="start",
                ),
                spacing="4",
                class_name="w-full p-2 hover:bg-gray-100 rounded-lg cursor-pointer",
            ),
            align_items="stretch",
            padding_x="4",
            spacing="3",
        ),
        align_items="stretch",
    )

def sidebar(state=None) -> rx.Component:
    """
    Sidebar component that can be used in multiple pages
    Args:
        state: Optional state object to use for the active tab.
               If None, will import MatchState as default.
    """
    # Import the state class here to avoid circular imports, only if state is not provided
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
                        class_name="w-10 h-10 bg-white rounded-full p-1 hover:bg-blue-500 hover:text-white",
                    ),
                    rx.icon(
                        "shield",
                        color="black",
                        class_name="w-10 h-10 bg-white rounded-full p-1 hover:bg-green-500 hover:text-white",
                    ),
                    rx.icon(
                        "settings",
                        color="black",
                        class_name="w-10 h-10 bg-white rounded-full p-1 hover:bg-red-500 hover:text-white",
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
                    "Liked",
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
                    "Messages",
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
            align_items="stretch",
            height="full",
        ),
        class_name="w-[350px] h-screen bg-sky-100 border-r border-gray-800",
    )