import reflex as rx
from typing import List, Dict, Any, TypedDict, Optional
from .SideBar import sidebar
import httpx
from ..Auth.AuthPage import AuthState

class ContactLink(TypedDict):
    url: str
    type: str

class Profile(TypedDict):
    id: int
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    bio: str
    industry: str
    experience: str
    skills: List[str]
    contact_links: List[ContactLink]

class MatchState(rx.State):
    """State for the matcher page."""
    current_profile_index: int = 0
    show_report_dialog: bool = False
    selected_issue_type: str = ""
    profiles: List[Profile] = []
    error_message: str = ""
    loading: bool = True
    API_BASE_URL = "http://100.95.107.24:8000/api/matches"
    active_tab: str = "Matches"
    
    async def on_mount(self):
        """Load potential matches when the page mounts."""
        await self.load_potential_matches()
    
    async def load_potential_matches(self):
        """Load potential matches from the API."""
        self.loading = True
        self.error_message = ""
        
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            # If token is None, try to get it from localStorage
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    # Update AuthState with the token from localStorage
                    auth_state.set_token(auth_token)
            
            if not auth_token:
                self.error_message = "Authentication required. Please log in."
                self.loading = False
                return
            
            # Make API request to get potential matches
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/potential-matches/",
                    headers={
                        "Authorization": f"Token {auth_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    self.profiles = response.json()
                    self.current_profile_index = 0 if self.profiles else -1
                elif response.status_code == 401:
                    self.error_message = "Authentication failed. Please log in again."
                    return rx.redirect("/login")
                else:
                    self.error_message = f"Error loading matches: {response.text}"
        except Exception as e:
            self.error_message = f"Error: {str(e)}"
        
        self.loading = False
    
    def next_profile(self):
        """Show the next profile."""
        if self.current_profile_index < len(self.profiles) - 1:
            self.current_profile_index += 1
    
    def previous_profile(self):
        """Show the previous profile."""
        if self.current_profile_index > 0:
            self.current_profile_index -= 1
    
    async def like_profile(self):
        """Like the current profile."""
        if self.current_profile_index < 0 or self.current_profile_index >= len(self.profiles):
            return
            
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            # If token is None, try to get it from localStorage
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    # Update AuthState with the token from localStorage
                    auth_state.set_token(auth_token)
            
            if not auth_token:
                self.error_message = "Authentication required. Please log in."
                return
            
            # Get the current profile
            current_profile = self.profiles[self.current_profile_index]
            
            # Make API request to like the profile
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/likes/",
                    headers={
                        "Authorization": f"Token {auth_token}",
                        "Content-Type": "application/json"
                    },
                    json={"liked_user": current_profile["id"]}
                )
                
                if response.status_code == 201:
                    # Check if there's a match
                    data = response.json()
                    if data.get("match"):
                        # Show match notification
                        self.error_message = f"It's a match with {current_profile['first_name']} {current_profile['last_name']}!"
                elif response.status_code == 401:
                    self.error_message = "Authentication failed. Please log in again."
                    return rx.redirect("/login")
                else:
                    self.error_message = f"Error liking profile: {response.text}"
        except Exception as e:
            self.error_message = f"Error: {str(e)}"
        
        # Move to next profile
        self.next_profile()
    
    async def dislike_profile(self):
        """Dislike the current profile."""
        if self.current_profile_index < 0 or self.current_profile_index >= len(self.profiles):
            return
            
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            # If token is None, try to get it from localStorage
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    # Update AuthState with the token from localStorage
                    auth_state.set_token(auth_token)
            
            if not auth_token:
                self.error_message = "Authentication required. Please log in."
                return
            
            # Get the current profile
            current_profile = self.profiles[self.current_profile_index]
            
            # Make API request to dislike the profile
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/dislikes/",
                    headers={
                        "Authorization": f"Token {auth_token}",
                        "Content-Type": "application/json"
                    },
                    json={"disliked_user": current_profile["id"]}
                )
                
                if response.status_code != 201 and response.status_code != 401:
                    self.error_message = f"Error disliking profile: {response.text}"
                elif response.status_code == 401:
                    self.error_message = "Authentication failed. Please log in again."
                    return rx.redirect("/login")
        except Exception as e:
            self.error_message = f"Error: {str(e)}"
        
        # Move to next profile
        self.next_profile()
    
    async def super_like_profile(self):
        """Super like the current profile."""
        # For now, just like the profile
        await self.like_profile()
    
    def set_active_tab(self, tab: str):
        """Set the active tab."""
        self.active_tab = tab

    def set_selected_issue_type(self, issue_type: str):
        """Set the selected issue type."""
        self.selected_issue_type = issue_type

def profile_card() -> rx.Component:
    """Render the profile card component."""
    return rx.box(
        rx.cond(
            MatchState.loading,
            rx.center(
                rx.spinner(size="3", color="white"),
                class_name="h-[500px] flex items-center justify-center"
            ),
            rx.cond(
                MatchState.error_message,
                rx.center(
                    rx.vstack(
                        rx.heading("Error", size="4", color="red.500"),
                        rx.text(MatchState.error_message, color="white"),
                        rx.button(
                            "Try Again",
                            on_click=MatchState.load_potential_matches,
                            class_name="mt-4 px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700"
                        ),
                        align_items="center",
                        spacing="4"
                    ),
                    class_name="h-[500px] flex items-center justify-center"
                ),
                rx.cond(
                    MatchState.current_profile_index >= 0 & (MatchState.profiles != []),
                    rx.vstack(
                        # Profile Image
                        rx.image(
                            src=rx.cond(
                                MatchState.profiles[MatchState.current_profile_index]["profile_picture_url"] != None,
                                MatchState.profiles[MatchState.current_profile_index]["profile_picture_url"],
                                "/assets/mock-image.jpg"
                            ),
                            class_name="w-48 h-48 rounded-full object-cover border-4 border-white shadow-lg"
                        ),
                        # Name
                        rx.heading(
                            f"{MatchState.profiles[MatchState.current_profile_index]['first_name']} {MatchState.profiles[MatchState.current_profile_index]['last_name']}",
                            size="4",
                            color="white",
                            class_name="mt-4"
                        ),
                        # Username
                        rx.text(
                            f"@{MatchState.profiles[MatchState.current_profile_index]['username']}",
                            color="gray.300",
                            class_name="mb-2"
                        ),
                        # Bio
                        rx.box(
                            rx.text(
                                MatchState.profiles[MatchState.current_profile_index]["bio"],
                                color="white",
                                class_name="text-center"
                            ),
                            class_name="max-w-md mx-auto mb-4"
                        ),
                        # Skills
                        rx.box(
                            rx.heading("Skills", size="3", color="white", class_name="mb-2"),
                            rx.flex(
                                rx.text(
                                    "Skills information available",
                                    color="white",
                                    class_name="text-center"
                                ),
                                wrap="wrap",
                                justify="center"
                            ),
                            class_name="mb-4"
                        ),
                        # Contact Links
                        rx.hstack(
                            rx.text(
                                "Contact information available",
                                color="white",
                                class_name="text-center"
                            ),
                            justify="center",
                            class_name="mt-2"
                        ),
                        width="100%",
                        max_width="600px",
                        padding="8",
                        class_name="bg-gray-800 rounded-xl shadow-2xl"
                    ),
                    rx.center(
                        rx.vstack(
                            rx.heading("No More Profiles", size="4", color="white"),
                            rx.text("Check back later for more potential matches!", color="gray.300"),
                            rx.button(
                                "Refresh",
                                on_click=MatchState.load_potential_matches,
                                class_name="mt-4 px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700"
                            ),
                            align_items="center",
                            spacing="4"
                        ),
                        class_name="h-[500px] flex items-center justify-center"
                    )
                )
            )
        ),
        class_name="w-full max-w-2xl mx-auto"
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
                    # Error message display
                    rx.cond(
                        MatchState.error_message,
                        rx.box(
                            rx.text(
                                MatchState.error_message,
                                color="white",
                                class_name="bg-red-600 p-3 rounded-lg mb-4"
                            ),
                            width="100%",
                            max_width="600px",
                        ),
                        rx.fragment()
                    ),
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
