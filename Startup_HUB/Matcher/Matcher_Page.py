import reflex as rx
from typing import List, Dict

class MatchState(rx.State):
    """State for the matcher page."""
    current_profile_index: int = 0
    profiles: List[Dict] = [
        {
            "name": "Soukaku",
            "profession": "Finance Consultant",
            "image": "character.jpg",
            "is_active": True
        },
        {
            "name": "Alex Chen",
            "profession": "Software Developer",
            "image": "character.jpg",
            "is_active": False
        },
        {
            "name": "Sarah Smith",
            "profession": "Marketing Specialist",
            "image": "character.jpg",
            "is_active": True
        }
    ]
    active_tab: str = "Matches"
    
    def next_profile(self):
        """Show the next profile."""
        if self.current_profile_index < len(self.profiles) - 1:
            self.current_profile_index += 1
    
    def previous_profile(self):
        """Show the previous profile."""
        if self.current_profile_index > 0:
            self.current_profile_index -= 1
    
    def like_profile(self):
        """Like the current profile."""
        # Add like logic here
        self.next_profile()
    
    def dislike_profile(self):
        """Dislike the current profile."""
        # Add dislike logic here
        self.next_profile()
    
    def super_like_profile(self):
        """Super like the current profile."""
        # Add super like logic here
        self.next_profile()

    def set_active_tab(self, tab: str):
        """Set the active tab."""
        self.active_tab = tab

def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Top section with search and icons
            rx.hstack(
                rx.avatar(
                    src="profile.jpg",
                    size="3",
                    class_name="cursor-pointer",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.icon("search", color="gray.400"),
                    rx.icon("shield", color="gray.400"),
                    rx.icon("settings", color="gray.400"),
                    spacing="4",
                ),
                width="full",
                padding="4",
            ),
            # Navigation tabs
            rx.hstack(
                rx.text(
                    "Matches",
                    color=rx.cond(MatchState.active_tab == "Matches", "white", "gray.400"),
                    font_weight="bold",
                    cursor="pointer",
                    on_click=lambda: MatchState.set_active_tab("Matches"),
                ),
                rx.text(
                    "liked",
                    color=rx.cond(MatchState.active_tab == "Liked", "white", "gray.400"),
                    font_weight="bold",
                    cursor="pointer",
                    on_click=lambda: MatchState.set_active_tab("Liked"),
                ),
                rx.text(
                    "Messages",
                    color=rx.cond(MatchState.active_tab == "Messages", "white", "gray.400"),
                    font_weight="bold",
                    cursor="pointer",
                    on_click=lambda: MatchState.set_active_tab("Messages"),
                ),
                spacing="6",
                padding="4",
            ),
            # Profile thumbnails
            rx.vstack(
                rx.image(
                    src="character.jpg",
                    class_name="w-16 h-16 rounded-lg object-cover cursor-pointer hover:opacity-80",
                ),
                align_items="start",
                padding_x="4",
                spacing="3",
            ),
            align_items="stretch",
            height="full",
        ),
        class_name="w-64 h-screen bg-[#1e1e1e] border-r border-gray-800",
    )

def profile_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.image(
                src=MatchState.profiles[MatchState.current_profile_index]["image"],
                class_name="w-full h-[500px] object-cover rounded-3xl",
            ),
            rx.box(
                rx.hstack(
                    rx.box(
                        class_name=rx.cond(
                            MatchState.profiles[MatchState.current_profile_index]["is_active"],
                            "w-2 h-2 rounded-full bg-green-400",
                            "w-2 h-2 rounded-full bg-gray-400"
                        ),
                    ),
                    rx.text(
                        rx.cond(
                            MatchState.profiles[MatchState.current_profile_index]["is_active"],
                            "Recently Active",
                            "Offline"
                        ),
                        class_name="text-gray-400 text-sm",
                    ),
                    spacing="2",
                ),
                rx.heading(
                    MatchState.profiles[MatchState.current_profile_index]["name"],
                    size="2",
                    class_name="text-white",
                ),
                rx.text(
                    f"Profession: {MatchState.profiles[MatchState.current_profile_index]['profession']}",
                    class_name="text-gray-400",
                ),
                padding="4",
                spacing="2",
                class_name="w-full bg-[#1e1e1e] rounded-b-3xl",
            ),
            spacing="0",
            width="full",
        ),
        class_name="w-[400px] overflow-hidden shadow-xl",
    )

def action_buttons() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon("arrow-left"),
            on_click=MatchState.previous_profile,
            class_name="rounded-full p-4 bg-[#2e2e2e] text-yellow-400 hover:bg-gray-800 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("x"),
            on_click=MatchState.dislike_profile,
            class_name="rounded-full p-4 bg-[#2e2e2e] text-red-400 hover:bg-gray-800 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("star"),
            on_click=MatchState.super_like_profile,
            class_name="rounded-full p-4 bg-[#2e2e2e] text-blue-400 hover:bg-gray-800 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("check"),
            on_click=MatchState.like_profile,
            class_name="rounded-full p-4 bg-[#2e2e2e] text-green-400 hover:bg-gray-800 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("eye"),
            class_name="rounded-full p-4 bg-[#2e2e2e] text-orange-400 hover:bg-gray-800 transform transition-all hover:scale-110",
        ),
        spacing="3",
        justify="center",
        padding_y="6",
    )

def match_page() -> rx.Component:
    """The match page."""
    return rx.hstack(
        sidebar(),
        rx.box(
            rx.center(
                rx.vstack(
                    profile_card(),
                    action_buttons(),
                    spacing="0",
                ),
                padding_top="8",
            ),
            class_name="flex-1 min-h-screen bg-[#1a1a1a]",
        ),
        spacing="0",
        width="full",
        height="100vh",
        overflow="hidden",
    )