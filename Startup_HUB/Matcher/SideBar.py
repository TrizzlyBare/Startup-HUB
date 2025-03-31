import reflex as rx

def matches_content() -> rx.Component:
    """Content for the Matches tab."""
    return rx.vstack(
        rx.grid(
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
            columns="3",
            spacing="4",
            padding_x="4",
            align_items="center",
        ),
        align_items="stretch",
    )

def liked_content() -> rx.Component:
    """Content for the Liked tab."""
    return rx.vstack(
        rx.vstack(
            rx.hstack(
                rx.avatar(
                    src="../../profile.jpg",
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text("John Doe", font_weight="bold", class_name="text-black"),
                    rx.text("Software Engineer", class_name="text-gray-600"),
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
                    rx.text("Soukaku", font_weight="bold", class_name="text-black"),
                    rx.text("Product Designer", class_name="text-gray-600"),
                    align_items="start",
                ),
                spacing="4",
                class_name="w-full p-2 hover:bg-gray-100 rounded-lg cursor-pointer",
            ),
            rx.hstack(
                rx.avatar(
                    src="../../blue_cat.jpg",
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text("Blue Cat", font_weight="bold", class_name="text-black"),
                    rx.text("UX Researcher", class_name="text-gray-600"),
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

def messages_content() -> rx.Component:
    """Content for the Messages tab."""
    return rx.vstack(
        rx.vstack(
            rx.hstack(
                rx.avatar(
                    src="../../profile.jpg",
                    size="5",
                    class_name="rounded-full",
                ),
                rx.vstack(
                    rx.text("John Doe", font_weight="bold", class_name= "text-black" ),
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
                    rx.text("Soukaku", font_weight="bold" , class_name= "text-black"),
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
            align_items="stretch",
            height="full",
        ),
        class_name="w-[350px] h-screen bg-sky-100 border-r border-gray-800",
    )