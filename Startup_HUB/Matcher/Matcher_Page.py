import reflex as rx
from typing import List, Dict
from .SideBar import sidebar

class MatchState(rx.State):
    """State for the matcher page."""
    current_profile_index: int = 0
    show_report_dialog: bool = False
    selected_issue_type: str = ""
    profiles: List[Dict] = [
        {
            "name": "Soukaku",
            "profession": "Finance Consultant",
            "image": "../../Soukaku.jpg",
            "is_active": True
        },
        {
            "name": "Cozy Clover",
            "profession": "Software Developer",
            "image": "../../blue_cat.jpg",
            "is_active": False
        },
        {
            "name": "Jane Doe",
            "profession": "Marketing Specialist",
            "image": "../../Jane_Doe.jpg",
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

    def set_selected_issue_type(self, issue_type: str):
        """Set the selected issue type."""
        self.selected_issue_type = issue_type

def profile_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.image(
                src=MatchState.profiles[MatchState.current_profile_index]["image"],
                class_name="w-full h-[700px] object-cover rounded-3xl border-4 border-white mt-3",
            ),
            rx.box(
                rx.hstack(
                    rx.box(
                        class_name=rx.cond(
                            MatchState.profiles[MatchState.current_profile_index]["is_active"],
                            "w-3 h-3 rounded-full bg-green-400",
                            "w-3 h-3 rounded-full bg-gray-400"
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
                    size="7",
                    class_name="text-sky-400",
                ),
                rx.text(
                    f"Profession: {MatchState.profiles[MatchState.current_profile_index]['profession']}",
                    class_name="text-black",
                ),
                padding="4",
                spacing="2",
                class_name="w-full bg-sky-100 rounded-2xl p-2 mt-1",
            ),
            spacing="0",
            width="full",
        ),
        class_name="w-[400px] overflow-hidden shadow-xl",
    )

def action_buttons() -> rx.Component:
    return rx.hstack(
        rx.button(
            rx.icon("arrow-left", class_name="drop-shadow-lg"),
            on_click=MatchState.previous_profile,
            class_name="rounded-full font-bold w-12 h-12 bg-yellow-400 text-white hover:bg-yellow-500 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("x", class_name="drop-shadow-lg"),
            on_click=MatchState.dislike_profile,
            class_name="rounded-full w-14 h-14 bg-[#E74C3C] text-white hover:bg-CB4335 transform transition-all hover:scale-150",
        ),
        rx.button(
            rx.icon("star", class_name="drop-shadow-lg"),
            on_click=MatchState.super_like_profile,
            class_name="rounded-full w-12 h-12 bg-blue-400 text-white hover:bg-blue-500 transform transition-all hover:scale-110",
        ),
        rx.button(
            rx.icon("check", class_name="drop-shadow-lg"),
            on_click=MatchState.like_profile,
            class_name="rounded-full w-14 h-14 bg-green-400  text-white hover:bg-green-500 transform transition-all hover:scale-150",
        ),
        rx.button(
            rx.icon("eye", class_name="drop-shadow-lg"),
            class_name="rounded-full w-12 h-12 bg-orange-400  text-white hover:bg-orange-500 transform transition-all hover:scale-110",
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
                    align_items="center",
                ),
            ),
            class_name="flex-1 min-h-screen bg-gray-800 flex flex-col justify-center items-center",
        ),
        spacing="0",
        width="full",
        height="100vh",
        overflow="hidden",
    )
