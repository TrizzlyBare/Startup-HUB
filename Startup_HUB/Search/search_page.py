import reflex as rx
from typing import List, Dict
from ..Matcher.SideBar import sidebar

class StartupGroup(rx.Base):
    """The startup group model."""
    name: str
    description: str
    members: int
    join_requested: bool = False
    needed_positions: List[str] = ["Software Engineer", "Product Manager", "UI/UX Designer"]
    project_details: str = "This is a detailed description of the project, including its goals, current status, and future plans."
    tech_stack: List[str] = ["Python", "React", "AWS"]
    funding_stage: str = "Seed"
    team_size: int = 15

class SearchState(rx.State):
    """The search state."""
    search_query: str = ""
    search_results: List[StartupGroup] = [
        StartupGroup(
            name="Tech Innovators Hub",
            description="A collaborative space for tech entrepreneurs and innovators working on cutting-edge solutions",
            members=150,
            needed_positions=["Full Stack Developer", "Data Scientist", "DevOps Engineer"],
            project_details="Building an AI-powered platform for predictive analytics in healthcare.",
            tech_stack=["Python", "TensorFlow", "React", "AWS"],
            funding_stage="Series A",
            team_size=25,
        ),
        StartupGroup(
            name="FinTech Founders Circle", 
            description="Network of founders revolutionizing financial technology and digital payments",
            members=120,
            needed_positions=["Blockchain Developer", "Security Engineer", "Product Manager"],
            project_details="Developing a decentralized finance platform for cross-border payments.",
            tech_stack=["Solidity", "React", "Node.js", "MongoDB"],
            funding_stage="Seed",
            team_size=18,
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
    active_tab: str = "Matches"
    show_details_modal: bool = False
    selected_group: StartupGroup | None = None

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

def show_startup(startup: StartupGroup):
    """Show a startup group in a styled box."""
    return rx.box(
        rx.vstack(
            rx.heading(startup.name, size="7", class_name="text-sky-600 font-bold pt-2 px-2 font-sans"),
            rx.text(
                startup.description,
                color="black",
                noOfLines=3,
                class_name="text-base font-small pt-2 px-2",
            ),
            rx.hstack(
                rx.text(f"Members: {startup.members}", color="black", class_name="text-lg font-medium pt-2 pl-1"),
                rx.spacer(),
                rx.hstack(
                    rx.cond(
                        startup.join_requested,
                        rx.button(
                            "Request Sent",
                            color_scheme="grass",
                            variant="outline",
                            is_disabled=True,
                            class_name="bg-sky-50 text-gray-700 hover:bg-sky-100 px-6 py-2 rounded-lg font-medium",
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
                        class_name="bg-gray-600 text-white hover:bg-gray-700 px-6 py-2 rounded-lg font-medium",
                    ),
                    spacing="4",
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
                class_name="text-2xl font-bold text-sky-600",
            ),
            rx.dialog.description(
                rx.vstack(
                    rx.text(
                        "Project Details",
                        class_name="text-xl font-semibold text-gray-700 mb-2",
                    ),
                    rx.cond(
                        SearchState.selected_group,
                        rx.text(
                            SearchState.selected_group.project_details,
                            class_name="text-gray-600 mb-4",
                        ),
                        rx.text("")
                    ),
                    rx.text(
                        "Needed Positions",
                        class_name="text-xl font-semibold text-gray-700 mb-2",
                    ),
                    rx.cond(
                        SearchState.selected_group,
                        rx.unordered_list(
                            rx.foreach(
                                SearchState.selected_group.needed_positions,
                                lambda pos: rx.list_item(
                                    pos,
                                    class_name="text-gray-600"
                                ),
                            ),
                            class_name="list-disc pl-5 mb-4",
                        ),
                        rx.text("")
                    ),
                    rx.text(
                        "Tech Stack",
                        class_name="text-xl font-semibold text-gray-700 mb-2",
                    ),
                    rx.cond(
                        SearchState.selected_group,
                        rx.hstack(
                            rx.foreach(
                                SearchState.selected_group.tech_stack,
                                lambda tech: rx.box(
                                    tech,
                                    class_name="bg-sky-100 text-sky-700 px-3 py-1 rounded-full m-1",
                                ),
                            ),
                            wrap="wrap",
                        ),
                        rx.text("")
                    ),
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "Funding Stage",
                                class_name="font-semibold text-gray-700",
                            ),
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
                            rx.text(
                                "Team Size",
                                class_name="font-semibold text-gray-700",
                            ),
                            rx.cond(
                                SearchState.selected_group,
                                rx.text(
                                    str(SearchState.selected_group.team_size),
                                    class_name="text-gray-600",
                                ),
                                rx.text("")
                            ),
                        ),
                        spacing="8",
                    ),
                    spacing="4",
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

def search_page() -> rx.Component:
    return rx.hstack(
        sidebar(SearchState),
        rx.box(
            rx.container(
                rx.vstack(
                    rx.heading("Startup Groups", size="9", mb=8, class_name="text-sky-400"),
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
                    rx.cond(
                        SearchState.is_loading,
                        rx.spinner(),
                        rx.cond(
                            SearchState.search_results,
                            rx.grid(
                                rx.foreach(
                                    SearchState.search_results,
                                    lambda startup: rx.box(
                                        show_startup(startup),
                                        width="45%",
                                    ),
                                ),
                                columns="2",
                                spacing="8",
                                width="100%",
                                template_columns="repeat(2, 1fr)",
                                gap="16",
                                padding="16",
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
                px="8",
                max_width="1400px",
                align="center",
                justify="center",
            ),
            class_name="flex-1 min-h-screen bg-gray-800 flex flex-col justify-center items-center px-4",
        ),
        details_modal(),
        align_items="stretch",
        spacing="0",
        width="full",
        height="100vh",
        overflow="hidden",
    )

    