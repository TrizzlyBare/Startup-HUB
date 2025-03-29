import reflex as rx
from typing import List, Dict
from ..Matcher.SideBar import sidebar

class StartupGroup(rx.Base):
    """The startup group model."""
    name: str
    description: str
    members: int
    join_requested: bool = False

class SearchState(rx.State):
    """The search state."""
    search_query: str = ""
    search_results: List[StartupGroup] = [
        StartupGroup(
            name="Tech Innovators Hub",
            description="A collaborative space for tech entrepreneurs and innovators working on cutting-edge solutions",
            members=150,
        ),
        StartupGroup(
            name="FinTech Founders Circle", 
            description="Network of founders revolutionizing financial technology and digital payments",
            members=120,
        ),
        StartupGroup(
            name="Green Energy Ventures",
            description="Community of startups focused on sustainable energy solutions",
            members=85,
        ),
        StartupGroup(
            name="HealthTech Alliance",
            description="Healthcare technology innovators improving patient care through digital solutions",
            members=95,
        ),
        StartupGroup(
            name="AI Research Collective",
            description="Group of AI and machine learning startups pushing the boundaries of artificial intelligence",
            members=175,
        ),
        StartupGroup(
            name="E-commerce Innovation",
            description="Entrepreneurs building the future of online retail and digital commerce",
            members=145,
        ),
    ]
    is_loading: bool = False
    active_tab: str = "Matches"  # Add this for sidebar state

    def request_to_join(self, group_name: str):
        """Send a request to join a startup group."""
        for group in self.search_results:
            if group.name == group_name:
                group.join_requested = True

    def set_search_query(self, query: str):
        """Set the search query."""
        self.search_query = query
    
    def search_startups(self):
        """Search for startup groups based on the query."""
        self.is_loading = True
        
        if not self.search_query:
            # If no query, show all results
            self.is_loading = False
            return
            
        # Filter results based on search query
        filtered_results = [
            group for group in self.search_results 
            if self.search_query.lower() in group.name.lower() or 
               self.search_query.lower() in group.description.lower()
        ]
        
        self.search_results = filtered_results
        self.is_loading = False

    def set_active_tab(self, tab: str):
        """Set the active tab in the sidebar."""
        self.active_tab = tab

def show_startup(startup: StartupGroup):
    """Show a startup group in a styled box."""
    return rx.box(
        rx.vstack(
            rx.heading(startup.name, size="1", class_name="text-sky-600 font-bold"),  # Changed to sky blue
            rx.text(
                startup.description,
                color="black",  # Keeping description dark
                noOfLines=3,
                class_name="text-lg font-medium",
            ),
            rx.hstack(
                rx.text(f"Members: {startup.members}", color="black", class_name="text-lg font-medium"),
                rx.spacer(),
                rx.cond(
                    startup.join_requested,
                    rx.button(
                        "Request Sent",
                        color_scheme="grass",
                        variant="outline",
                        is_disabled=True,
                        class_name="bg-sky-50 text-gray-700 hover:bg-sky-100 px-6 py-2 rounded-full font-medium",
                    ),
                    rx.button(
                        "Join Group",
                        on_click=lambda: SearchState.request_to_join(startup.name),
                        class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-full font-medium",  # Updated button to match heading
                    ),
                ),
                width="100%"
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
        min_width="400px",
        height="100%",
        class_name="bg-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 rounded-lg",
    )

def search_page() -> rx.Component:
    return rx.hstack(
        sidebar(SearchState),
        rx.box(
            rx.container(
                rx.vstack(
                    rx.heading("Startup Groups", size="3", mb=8, class_name="text-sky-400"),
                    rx.hstack(
                        rx.input(
                            placeholder="Search groups...",
                            value=SearchState.search_query,
                            on_change=SearchState.set_search_query,
                            size="3",
                            width="100%",
                            class_name="bg-gray-700 text-white border-gray-600",
                        ),
                        rx.button(
                            "Search",
                            on_click=SearchState.search_startups,
                            size="3",
                            class_name="bg-sky-400 text-white hover:bg-sky-500",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    rx.cond(
                        SearchState.is_loading,
                        rx.spinner(),
                        rx.cond(
                            SearchState.search_results,
                            rx.grid(
                                rx.foreach(
                                    SearchState.search_results,
                                    show_startup
                                ),
                                columns="2",  # Changed to 2 columns for wider cards
                                spacing="8",
                                width="100%",
                                template_columns="repeat(2, minmax(400px, 1fr))",  # Added template columns
                                padding="8",
                            ),
                            rx.text("No results found. Try a different search term.", color="gray.300"),
                        ),
                    ),
                    spacing="8",
                    width="100%",
                    align="center",
                    justify="center",
                ),
                py=8,
                px="16",  # Increased horizontal padding
                max_width="1800px",  # Set a max width for better layout
                align="center",
                justify="center",
            ),
            class_name="flex-1 min-h-screen bg-gray-800 flex flex-col justify-center items-center px-20",  # Increased padding
        ),
        align_items="stretch",
        spacing="0",
        width="full",
        height="100vh",
        overflow="hidden",
    )