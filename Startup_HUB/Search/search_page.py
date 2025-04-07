import reflex as rx
import httpx
from typing import List, Dict, Optional
from ..Matcher.SideBar import sidebar
from ..Auth.AuthPage import AuthState

class Member(rx.Base):
    """A member model."""
    id: int
    username: str
    profile_picture_url: Optional[str]
    skills: Optional[str] = None
    industry: Optional[str] = None

class Owner(rx.Base):
    """An owner model."""
    id: int
    username: str
    profile_picture: Optional[str]

class StartupGroup(rx.Base):
    """The startup group model."""
    id: int
    username: str
    user_profile_picture: Optional[str]
    owner: Owner
    name: str
    stage: str
    user_role: str
    user_role_display: str
    pitch: str
    description: str
    skills: str
    skills_list: List[str]
    looking_for: str
    looking_for_list: List[str]
    pitch_deck_url: Optional[str]
    images: List[str]
    website: str
    funding_stage: str
    investment_needed: str
    members: List[Member]
    member_count: int
    created_at: str
    updated_at: str
    join_requested: bool = False

class SearchState(rx.State):
    """The search state."""
    # API endpoint - base URL
    API_URL = "http://startup-hub:8000/api"
    
    search_query: str = ""
    search_results: List[StartupGroup] = []
    is_loading: bool = False
    active_tab: str = "Matches"
    show_details_modal: bool = False
    selected_group: StartupGroup | None = None
    error: Optional[str] = None
    total_count: int = 0
    next_page: Optional[str] = None
    previous_page: Optional[str] = None
    
    # Notification states
    show_notification: bool = False
    notification_type: str = "info"  # info, success, error
    notification_title: str = ""
    notification_message: str = ""

    async def on_mount(self):
        """Fetch all projects when the page loads."""
        print("Search page mounted - fetching all projects...")
        await self.search_startups()

    async def search_startups(self):
        """Search for startup groups based on the query."""
        self.is_loading = True
        print(f"\n=== Loading Projects ===")
        
        try:
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            print(f"Making API request to: {self.API_URL}/startup-profile/startup-ideas/all-projects/")
            
            async with httpx.AsyncClient() as client:
                # Get all projects without any filters
                response = await client.get(
                    f"{self.API_URL}/startup-profile/startup-ideas/all-projects/",
                    headers=headers
                )
                
                print(f"Response Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"API Response data received. Count: {data.get('count', 0)}")
                    
                    # Update pagination info
                    self.total_count = data.get("count", 0)
                    self.next_page = data.get("next")
                    self.previous_page = data.get("previous")
                    
                    # Handle both list and paginated response formats
                    results = data.get("results", []) if isinstance(data, dict) else data
                    print(f"Number of results: {len(results)}")
                    
                    self.search_results = []
                    for item in results:
                        try:
                            # Convert images to list of strings if needed
                            images_list = []
                            if "images" in item:
                                if isinstance(item["images"], list):
                                    images_list = [str(img) for img in item["images"]]
                                else:
                                    # If images is not a list, make it an empty list
                                    images_list = []
                            
                            # Create StartupGroup with validated data
                            group = StartupGroup(
                                id=item["id"],
                                username=item["username"],
                                user_profile_picture=item["user_profile_picture"],
                                owner=Owner(
                                    id=item["owner"]["id"],
                                    username=item["owner"]["username"],
                                    profile_picture=item["owner"]["profile_picture"]
                                ),
                                name=item["name"],
                                stage=item["stage"],
                                user_role=item["user_role"],
                                user_role_display=item["user_role_display"],
                                pitch=item["pitch"],
                                description=item["description"],
                                skills=item["skills"],
                                skills_list=item["skills_list"],
                                looking_for=item["looking_for"],
                                looking_for_list=item["looking_for_list"],
                                pitch_deck_url=item["pitch_deck_url"],
                                images=images_list,
                                website=item["website"],
                                funding_stage=item["funding_stage"],
                                investment_needed=item["investment_needed"],
                                members=[
                                    Member(
                                        id=member["id"],
                                        username=member["username"],
                                        profile_picture_url=member["profile_picture_url"],
                                        skills=member["skills"],
                                        industry=member["industry"]
                                    )
                                    for member in item["members"]
                                ],
                                member_count=item["member_count"],
                                created_at=item["created_at"],
                                updated_at=item["updated_at"]
                            )
                            self.search_results.append(group)
                        except Exception as e:
                            print(f"Error processing result item: {str(e)}")
                            # Continue processing other items even if one fails
                            continue
                            
                    print(f"Successfully mapped {len(self.search_results)} projects")
                elif response.status_code == 401:
                    print("Authentication failed")
                    return rx.redirect("/login")
                else:
                    self.error = f"Failed to load projects: {response.text}"
                    print(f"Error loading projects: {response.text}")
        except Exception as e:
            self.error = str(e)
            print(f"Exception in search_startups: {str(e)}")
        finally:
            self.is_loading = False
            print("=== Finished Loading Projects ===\n")

    def set_search_query(self, query: str):
        """Set the search query."""
        self.search_query = query

    async def request_to_join(self, group_name: str):
        """Send a request to join a startup group and email the owner."""
        try:
            # Find the group by name
            target_group = None
            for group in self.search_results:
                if group.name == group_name:
                    target_group = group
                    break
            
            if not target_group:
                print(f"Group with name '{group_name}' not found")
                self.show_error_notification(
                    "Group Not Found", 
                    f"Couldn't find group '{group_name}'"
                )
                return
            
            # Get token from AuthState
            auth_state = await self.get_state(AuthState)
            auth_token = auth_state.token
            
            if not auth_token:
                auth_token = await rx.call_script("localStorage.getItem('auth_token')")
                if auth_token:
                    auth_state.set_token(auth_token)
                else:
                    return rx.redirect("/login")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {auth_token}"
            }
            
            # Send request to join
            print(f"Sending request to join startup group: {target_group.name} (ID: {target_group.id})")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.API_URL}/startup-profile/startup-ideas/{target_group.id}/request-to-join/",
                    headers=headers
                )
                
                if response.status_code == 200 or response.status_code == 201:
                    print(f"Successfully sent request to join group: {target_group.name}")
                    # Update UI to show request sent
                    target_group.join_requested = True
                    self.show_success_notification(
                        "Request Sent", 
                        f"Successfully sent join request to {target_group.name}. The owner will be notified by email."
                    )
                else:
                    print(f"Failed to send join request. Status: {response.status_code}, Response: {response.text}")
                    self.error = f"Failed to send join request: {response.text}"
                    self.show_error_notification(
                        "Request Failed", 
                        "Failed to send join request. Please try again later."
                    )
        except Exception as e:
            print(f"Exception in request_to_join: {str(e)}")
            self.error = str(e)
            self.show_error_notification(
                "Error", 
                f"An error occurred: {str(e)}"
            )

    def set_active_tab(self, tab: str):
        """Set the active tab in the sidebar."""
        self.active_tab = tab

    def show_group_details(self, group: StartupGroup):
        """Show the details modal for a specific group."""
        self.selected_group = group
        self.show_details_modal = True

    def close_details_modal(self):
        """Close the details modal."""
        self.show_details_modal = False
        self.selected_group = None

    def show_my_projects(self):
        """Show the my projects page."""
        self.active_tab = "My Projects"
        return rx.redirect("/my-projects")
        
    def show_success_notification(self, title: str, message: str):
        """Show a success notification."""
        self.notification_type = "success"
        self.notification_title = title
        self.notification_message = message
        self.show_notification = True
        
    def show_error_notification(self, title: str, message: str):
        """Show an error notification."""
        self.notification_type = "error"
        self.notification_title = title
        self.notification_message = message
        self.show_notification = True
        
    def hide_notification(self):
        """Hide the notification."""
        self.show_notification = False

def show_startup(startup: StartupGroup):
    """Show a startup group in a styled box."""
    return rx.box(
        rx.vstack(
            # Header with name and owner info
            rx.hstack(
                rx.avatar(
                    src=startup.owner.profile_picture,
                    fallback=startup.owner.username[0].upper(),
                    size="5",
                ),
                rx.vstack(
                    rx.heading(startup.name, size="6", class_name="text-sky-600 font-bold font-mono"),
                    rx.text(f"by {startup.owner.username}",size="3", class_name="text-gray-500 "),
                    align_items="start",
                ),
                justify="start",
                width="100%",
                spacing="3",
            ),
            # Description
            rx.text(
                f"description : {startup.description}",
                color="black",
                noOfLines=3,
                class_name="text-base font-small pt-2 pl-2",
            ),
            # Skills and Looking For
            rx.vstack(
                rx.text("Skills Needed:",size = "3" ,  class_name="font-bold text-sky-400 ml-2"),
                rx.flex(
                    rx.foreach(
                        startup.skills_list,
                        lambda skill: rx.box(
                            skill,
                            class_name="bg-sky-100 text-sky-700 px-3 py-1 rounded-full m-1 text-sm",
                        ),
                    ),
                    wrap="wrap",
                    spacing="1",
                ),
                rx.text("Looking For:",size ="3", class_name="font-bold text-sky-400 ml-2"),
                rx.flex(
                    rx.foreach(
                        startup.looking_for_list,
                        lambda role: rx.box(
                            role,
                            class_name="bg-green-100 text-green-700 px-3 py-1 rounded-full m-1 text-sm",
                        ),
                    ),
                    wrap="wrap",
                    spacing="1",
                ),
                align_items="start",
                width="100%",
            ),
            # Footer with stats and actions
            rx.hstack(
                rx.vstack(
                    rx.text(f"Members: {startup.member_count}", class_name="font-bold text-black ml-2"),
                    rx.text(f"Stage: {startup.stage}", class_name="font-bold text-black ml-2 mb-2"),
                    align_items="start",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.cond(
                        startup.join_requested,
                        rx.button(
                            "Request Sent",
                            color_scheme="grass",
                            variant="outline",
                            is_disabled=True,
                            class_name="bg-green-50 text-gray-700 hover:bg-green-100 px-6 py-2 rounded-lg font-medium",
                        ),
                        rx.button(
                            "Join Group",
                            on_click=lambda: SearchState.request_to_join(startup.name),
                            class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium",
                        ),
                    ),
                    rx.button(
                        "View Details",
                        on_click=lambda: SearchState.show_group_details(startup),
                        class_name="bg-gray-600 text-white hover:bg-gray-700 px-6 py-2 rounded-lg font-medium mr-3",
                    ),
                    spacing="4",
                ),
                width="100%",
                align_items="center",
            ),
            spacing="4",
            height="100%",
            width="100%",
        ),
        p=8,
        border="1px solid",
        border_color="blue.200",
        border_radius="3xl",
        width="100%",
        min_width="450px",
        height="100%",
        class_name="bg-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 rounded-lg",
    )

def details_modal():
    """Show the details modal for a selected group."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(
                    SearchState.selected_group,
                    SearchState.selected_group.name,
                    "Group Details"
                ),
                class_name="text-3xl font-bold w-full text-sky-600 text-center font-mono"
            ),
            rx.dialog.description(
                rx.vstack(
                    # Owner Info
                    rx.hstack(
                        rx.avatar(
                            rx.cond(
                                SearchState.selected_group,
                                SearchState.selected_group.owner.profile_picture,
                                None
                            ),
                            rx.cond(
                                SearchState.selected_group,
                                SearchState.selected_group.owner.username[0].upper(),
                                ""
                            ),
                            size="5",
                        ),
                        rx.vstack(
                            rx.cond(
                                SearchState.selected_group,
                                rx.text(f"Created by {SearchState.selected_group.owner.username}", class_name="font-semibold text-gray-600"),
                                rx.text("")
                            ),
                            rx.cond(
                                SearchState.selected_group,
                                rx.text(f"Role: {SearchState.selected_group.user_role_display}", class_name="text-sky-600"),
                                rx.text("")
                            ),
                            align_items="start",
                        ),
                        spacing="4",
                    ),
                    # Pitch and Description
                    rx.vstack(
                        rx.text("Pitch", class_name="text-xl font-bold text-sky-600 mb-2"),
                        rx.cond(
                            SearchState.selected_group,
                            rx.text(
                                SearchState.selected_group.pitch,
                                class_name="text-black mb-4",
                            ),
                            rx.text("")
                        ),
                        rx.text("Description", class_name="text-xl font-bold text-sky-600 mb-2"),
                        rx.cond(
                            SearchState.selected_group,
                            rx.text(
                                SearchState.selected_group.description,
                                class_name="text-black mb-4",
                            ),
                            rx.text("")
                        ),
                        align_items="start",
                    ),
                    # Skills and Looking For
                    rx.vstack(
                        rx.text("Skills Needed", class_name="text-xl font-bold text-sky-600 mb-2"),
                        rx.cond(
                            SearchState.selected_group,
                            rx.flex(
                                rx.foreach(
                                    SearchState.selected_group.skills_list,
                                    lambda skill: rx.box(
                                        skill,
                                        class_name="bg-sky-100 text-sky-700 px-3 py-1 rounded-full m-1",
                                    ),
                                ),
                                wrap="wrap",
                                spacing="2",
                            ),
                            rx.text("")
                        ),
                        rx.text("Looking For", class_name="text-xl font-bold text-sky-600 mb-2 mt-4"),
                        rx.cond(
                            SearchState.selected_group,
                            rx.flex(
                                rx.foreach(
                                    SearchState.selected_group.looking_for_list,
                                    lambda role: rx.box(
                                        role,
                                        class_name="bg-green-100 text-green-700 px-3 py-1 rounded-full m-1",
                                    ),
                                ),
                                wrap="wrap",
                                spacing="2",
                            ),
                            rx.text("")
                        ),
                        align_items="start",
                    ),
                    # Project Details
                    rx.vstack(
                        rx.text("Project Details", class_name="text-xl font-bold text-sky-600 mb-2"),
                        rx.hstack(
                            rx.vstack(
                                rx.text("Stage", class_name="font-semibold text-black"),
                                rx.cond(
                                    SearchState.selected_group,
                                    rx.text(
                                        SearchState.selected_group.stage,
                                        class_name="text-gray-600",
                                    ),
                                    rx.text("")
                                ),
                            ),
                            rx.vstack(
                                rx.text("Funding Stage", class_name="font-semibold text-gray-700"),
                                rx.cond(
                                    SearchState.selected_group,
                                    rx.text(
                                        SearchState.selected_group.funding_stage,
                                        class_name="text-gray-600",
                                    ),
                                    rx.text("")
                                ),
                            ),
                            rx.vstack(
                                rx.text("Investment Needed", class_name="font-semibold text-gray-700"),
                                rx.cond(
                                    SearchState.selected_group,
                                    rx.text(
                                        f"${SearchState.selected_group.investment_needed}",
                                        class_name="text-green-600",
                                    ),
                                    rx.text("")
                                ),
                            ),
                            spacing="8",
                        ),
                        align_items="start",
                    ),
                    # Members
                    rx.vstack(
                        rx.text("Team Members", class_name="text-xl font-bold text-sky-600 mb-2"),
                        rx.cond(
                            SearchState.selected_group,
                            rx.vstack(
                                rx.foreach(
                                    SearchState.selected_group.members,
                                    lambda member: rx.hstack(
                                        rx.avatar(
                                            member.profile_picture_url,
                                            member.username[0].upper(),
                                            size="3",
                                        ),
                                        rx.vstack(
                                            rx.text(member.username, class_name="font-medium text-black"),
                                            rx.text(f"Skills: {member.skills}", class_name="text-sm text-gray-600"),
                                            rx.text(f"Industry: {member.industry}", class_name="text-sm text-gray-600 mb-2"),
                                            align_items="start",
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                ),
                                spacing="3",
                            ),
                            rx.text("")
                        ),
                        align_items="start",
                    ),
                    spacing="6",
                    width="100%",
                ),
            ),
            rx.dialog.close(
                rx.button(
                    "Close",
                    on_click=SearchState.close_details_modal,
                    class_name="bg-gray-600 text-white hover:bg-gray-700 px-6 py-2 rounded-lg font-medium",
                ),
            ),
            max_width="800px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-xl",
        ),
        open=SearchState.show_details_modal,
    )

def notification():
    """Custom notification component."""
    return rx.cond(
        SearchState.show_notification,
        rx.box(
            rx.hstack(
                rx.cond(
                    SearchState.notification_type == "success",
                    rx.icon("check", color="white", size=6),
                    rx.icon("alert-triangle", color="white", size=6)
                ),
                rx.vstack(
                    rx.text(
                        SearchState.notification_title,
                        font_weight="bold",
                        color="white",
                    ),
                    rx.text(
                        SearchState.notification_message,
                        color="white",
                    ),
                    align_items="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("x", size=4),
                    on_click=SearchState.hide_notification,
                    variant="ghost",
                    color_scheme="gray",
                ),
                width="100%",
                spacing="3",
            ),
            position="fixed",
            bottom="4",
            right="4",
            max_width="400px",
            p="4",
            border_radius="md",
            z_index="1000",
            shadow="lg",
            bg=rx.cond(
                SearchState.notification_type == "success",
                "green.500",
                "red.500"
            ),
            opacity="0.95",
        ),
        rx.fragment()
    )

def search_page() -> rx.Component:
    return rx.hstack(
        sidebar(SearchState),
        rx.box(
            rx.container(
                rx.vstack(
                    rx.heading("Startup Groups", size="9", mb=8, class_name="text-sky-300 font-serif"),
                    rx.hstack(
                        rx.input(
                            placeholder="Search groups...",
                            value=SearchState.search_query,
                            on_change=SearchState.set_search_query,
                            size="3",
                            width="100%",
                            class_name="bg-gray-400 text-white border-gray-600",
                        ),
                        rx.button(
                            "Search",
                            on_click=SearchState.search_startups,
                            size="3",
                            class_name="bg-sky-400 text-white hover:bg-sky-500",
                        ),
                        rx.button(
                            "My Projects",
                            on_click=SearchState.show_my_projects,
                            size="3",
                            class_name="bg-sky-400 text-white hover:bg-sky-500",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    # Add a spacer here to create more vertical distance
                    rx.box(height="24px"), 
                    # Wrap the results in a scrollable container
                    rx.box(
                        rx.cond(
                            SearchState.is_loading,
                            rx.center(rx.spinner(size="3"), width="100%", padding="40px"),
                            rx.cond(
                                SearchState.search_results,
                                rx.grid(
                                    rx.foreach(
                                        SearchState.search_results,
                                        lambda startup: rx.box(
                                            show_startup(startup),
                                            width="100%",
                                        ),
                                    ),
                                    columns="2",
                                    template_columns="repeat(2, 1fr)",
                                    gap="40px",
                                    width="100%",
                                ),
                                rx.text("No results found. Try a different search term.", color="gray.300", padding="40px"),
                            ),
                        ),
                        width="100%",
                        height="calc(100vh - 200px)",  # Fixed height with space for header and search
                        overflow_y="auto",  # Enable vertical scrolling
                        padding_top="10px", 
                        padding_bottom="40px",
                    ),
                    spacing="4",
                    width="100%",
                    height="100%",
                    align="center",
                ),
                py=8,
                px="8",
                max_width="1400px",
                height="100%",
            ),
            class_name="flex-1 min-h-screen bg-gray-800 flex flex-col items-center px-4 overflow-hidden",
        ),
        details_modal(),
        notification(),
        align_items="stretch",
        spacing="0",
        width="full",
        height="100vh",
        overflow="hidden",
    )

    