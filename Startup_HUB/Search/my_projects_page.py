import reflex as rx
from typing import List
from ..Matcher.SideBar import sidebar  # Keep your original import

class Project(rx.Base):
    """The project model."""
    name: str
    description: str 
    tech_stack: list[str] = []
    funding_stage: str = "Pre-seed"
    team_size: int = 1
    looking_for: list[str] = []

class MyProjectsState(rx.State):
    """The projects state."""
    projects: list[Project] = [
        Project(
            name="AI Health Assistant",
            description="A healthcare assistant powered by artificial intelligence.",
            tech_stack=["Python", "TensorFlow", "React Native"],
            funding_stage="Pre-seed",
            team_size=2,
            looking_for=["ML Engineer", "Mobile Dev"],
        ),
        Project(
            name="Eco Platform", 
            description="Sustainable delivery platform.",
            tech_stack=["React", "Node.js", "MongoDB"],
            funding_stage="Seed",
            team_size=3,
            looking_for=["Full Stack", "UI/UX"],
        ),
    ]
    new_project: Project = Project(name="", description="")
    show_modal: bool = False
    show_edit_modal: bool = False
    editing_project: Project = None
    active_tab: str = "My Projects"

    @rx.var
    def has_projects(self) -> bool:
        return len(self.projects) > 0

    @rx.event
    def set_active_tab(self, tab: str):
        """Set the active tab."""
        self.active_tab = tab

    @rx.event
    def toggle_modal(self):
        """Toggle the create modal."""
        self.show_modal = not self.show_modal

    @rx.event
    def toggle_edit_modal(self):
        """Toggle the edit modal."""
        self.show_edit_modal = not self.show_edit_modal

    @rx.event
    def start_edit(self, project: Project):
        """Start editing a project."""
        self.editing_project = project
        self.show_edit_modal = True

    @rx.event
    def edit_project(self, form_data: dict):
        """Edit a project."""
        if form_data["name"] and form_data["description"] and self.editing_project:
            # Find the project to edit
            for i, project in enumerate(self.projects):
                if project.name == self.editing_project.name:
                    # Update the project
                    self.projects[i] = Project(
                        name=form_data["name"],
                        description=form_data["description"],
                        tech_stack=form_data.get("tech_stack", "").split(",") if form_data.get("tech_stack") else [],
                        funding_stage=form_data.get("funding_stage", "Pre-seed"),
                        team_size=int(form_data.get("team_size", 1)),
                        looking_for=form_data.get("looking_for", "").split(",") if form_data.get("looking_for") else [],
                    )
                    break
            self.show_edit_modal = False
            self.editing_project = None

    @rx.event
    def create_project(self, form_data: dict):
        """Create a new project."""
        if form_data["name"] and form_data["description"]:
            self.projects.append(
                Project(
                    name=form_data["name"],
                    description=form_data["description"],
                    tech_stack=form_data.get("tech_stack", "").split(",") if form_data.get("tech_stack") else [],
                    funding_stage=form_data.get("funding_stage", "Pre-seed"),
                    team_size=int(form_data.get("team_size", 1)),
                    looking_for=form_data.get("looking_for", "").split(",") if form_data.get("looking_for") else [],
                )
            )
            self.show_modal = False

    @rx.event
    def delete_project(self, project_name: str):
        """Delete a project."""
        self.projects = [p for p in self.projects if p.name != project_name]

def show_project(project: rx.Var[Project]) -> rx.Component:
    """Show a project component."""
    return rx.box(
        rx.vstack(
            # Project header and description section
            rx.vstack(
                rx.heading(project.name, size="6", class_name="text-sky-600 font-bold p-2"),
                rx.text(
                    project.description,
                    noOfLines=3,
                    class_name="text-md font-small px-2 text-gray-400",
                ),
                width="100%",
                padding_x="12",
            ),
            
            # Project details section
            rx.vstack(
                rx.hstack(
                    rx.text(f"Team Size: {project.team_size}", color="black", class_name="text-md px-2"),
                    rx.text(f"Stage: {project.funding_stage}", color="black", class_name="text-md px-2"),
                    spacing="4",
                ),
                rx.text("Tech Stack:", color="black", class_name="text-lg font-medium mt-2 px-2"),
                rx.hstack(
                    rx.foreach(
                        project.tech_stack,
                        lambda tech: rx.box(
                            tech,
                            class_name="bg-sky-100 text-sky-700 px-3 py-1 rounded-full m-1 px-2",
                        ),
                    ),
                    wrap="wrap",
                ),
                rx.text("Looking for:", color="black", class_name="text-lg font-medium mt-2 px-2"),
                rx.hstack(
                    rx.foreach(
                        project.looking_for,
                        lambda role: rx.box(
                            role,
                            class_name="bg-green-100 text-green-700 px-3 py-1 rounded-full m-1 px-2",
                        ),
                    ),
                    wrap="wrap",
                ),
                align_items="start",
                width="100%",
                padding_x="24",
            ),
            
            # Buttons section - fixed at bottom
            rx.spacer(),  # This pushes the buttons to the bottom
            rx.hstack(
                rx.link(
                    rx.icon("pencil", class_name="w-8 h-8 text-sky-600 hover:text-sky-800 transition-colors"),
                    on_click=lambda: MyProjectsState.start_edit(project),
                    class_name="p-3 cursor-pointer",
                    title="Edit Project",
                ),
                rx.link(
                    rx.icon("trash", class_name="w-8 h-8 text-red-600 hover:text-red-800 transition-colors"),
                    on_click=lambda: MyProjectsState.delete_project(project.name),
                    class_name="p-3 cursor-pointer",
                    title="Delete Project",
                ),
                spacing="4",
                width="100%",
                justify="end",
                padding_x="12",
            ),
            height="100%",  # Make the vstack take full height
            align_items="stretch",  # Stretch children to full width
            spacing="6",  # Increased spacing between sections
            padding_x="12",  # Only horizontal padding
        ),
        p=8,
        border="1px solid",
        border_color="blue.200",
        border_radius="3xl",
        width="100%",
        min_width="400px",
        height="100%",
        class_name="bg-white shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 rounded-lg mx-4",
    )

def create_project_modal() -> rx.Component:
    """Create project modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header section
                rx.box(
                    rx.heading(
                        "Create New Project",
                        size="5",
                        class_name="text-sky-600 font-bold mb-2 text-3xl",
                    ),
                    rx.text(
                        "Fill in the details below to create your new project",
                        class_name="text-gray-600 mb-6",
                    ),
                    width="100%",
                ),
                
                # Form section
                rx.form(
                    rx.vstack(
                        # Project Name
                        rx.vstack(
                            rx.text("Project Name", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="Enter your project name",
                                name="name",
                                required=True,
                                class_name="w-full border border-gray-300 bg-sky-600 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Project Description
                        rx.vstack(
                            rx.text("Project Description", class_name="text-gray-700 font-medium"),
                            rx.text_area(
                                placeholder="Describe your project and its goals",
                                name="description",
                                required=True,
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 min-h-[150px] min-w-[500px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Tech Stack
                        rx.vstack(
                            rx.text("Tech Stack", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="e.g., Python, React, Node.js (comma-separated)",
                                name="tech_stack",
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 min-w-[500px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Funding Stage
                        rx.vstack(
                            rx.text("Funding Stage", class_name="text-gray-700 font-medium"),
                            rx.select(
                                ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                                placeholder="Select funding stage",
                                name="funding_stage",
                                class_name="w-full border border-gray-300 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Team Size
                        rx.vstack(
                            rx.text("Team Size", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="Number of team members",
                                name="team_size",
                                type="number",
                                min_value=1,
                                default_value="1",
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 max-w-[50px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Looking For
                        rx.vstack(
                            rx.text("Looking For", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="e.g., Frontend Dev, Backend Dev (comma-separated)",
                                name="looking_for",
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 min-w-[500px] min-h-[70px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="bg-gray-200 text-gray-700 hover:bg-gray-300 px-6 py-2 rounded-lg font-medium",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Create Project",
                                    type="submit",
                                    class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="6",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    on_submit=MyProjectsState.create_project,
                    reset_on_submit=True,
                ),
                width="100%",
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-xl",
        ),
        open=MyProjectsState.show_modal,
    )

def edit_project_modal() -> rx.Component:
    """Edit project modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                # Header section
                rx.box(
                    rx.heading(
                        "Edit Project",
                        size="5",
                        class_name="text-sky-600 font-bold mb-2 text-3xl",
                    ),
                    rx.text(
                        "Update your project details below",
                        class_name="text-gray-600 mb-6",
                    ),
                    width="100%",
                ),
                
                # Form section
                rx.form(
                    rx.vstack(
                        # Project Name
                        rx.vstack(
                            rx.text("Project Name", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="Enter your project name",
                                name="name",
                                required=True,
                                default_value=rx.cond(
                                    MyProjectsState.editing_project,
                                    MyProjectsState.editing_project.name,
                                    ""
                                ),
                                class_name="w-full border border-gray-300 bg-sky-600 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Project Description
                        rx.vstack(
                            rx.text("Project Description", class_name="text-gray-700 font-medium"),
                            rx.text_area(
                                placeholder="Describe your project and its goals",
                                name="description",
                                required=True,
                                default_value=rx.cond(
                                    MyProjectsState.editing_project,
                                    MyProjectsState.editing_project.description,
                                    ""
                                ),
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 min-h-[150px] min-w-[500px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Tech Stack
                        rx.vstack(
                            rx.text("Tech Stack", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="e.g., Python, React, Node.js (comma-separated)",
                                name="tech_stack",
                                default_value=rx.cond(
                                    MyProjectsState.editing_project,
                                    MyProjectsState.editing_project.tech_stack.join(","),
                                    ""
                                ),
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 min-w-[500px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Funding Stage
                        rx.vstack(
                            rx.text("Funding Stage", class_name="text-gray-700 font-medium"),
                            rx.select(
                                ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                                placeholder="Select funding stage",
                                name="funding_stage",
                                default_value=rx.cond(
                                    MyProjectsState.editing_project,
                                    MyProjectsState.editing_project.funding_stage,
                                    "Pre-seed"
                                ),
                                class_name="w-full border border-gray-300 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Team Size
                        rx.vstack(
                            rx.text("Team Size", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="Number of team members",
                                name="team_size",
                                type="number",
                                min_value=1,
                                default_value=rx.cond(
                                    MyProjectsState.editing_project,
                                    MyProjectsState.editing_project.team_size.to_string(),
                                    "1"
                                ),
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 max-w-[50px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Looking For
                        rx.vstack(
                            rx.text("Looking For", class_name="text-gray-700 font-medium"),
                            rx.input(
                                placeholder="e.g., Frontend Dev, Backend Dev (comma-separated)",
                                name="looking_for",
                                default_value=rx.cond(
                                    MyProjectsState.editing_project,
                                    MyProjectsState.editing_project.looking_for.join(","),
                                    ""
                                ),
                                class_name="w-full border border-gray-300 bg-gray-500 rounded-lg focus:border-sky-500 focus:ring-2 focus:ring-sky-200 min-w-[500px] min-h-[70px]",
                            ),
                            align_items="start",
                            spacing="2",
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                                on_click=MyProjectsState.toggle_edit_modal,
                                class_name="bg-gray-200 text-gray-700 hover:bg-gray-300 px-6 py-2 rounded-lg font-medium",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Changes",
                                    type="submit",
                                    class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="6",
                        ),
                        spacing="4",
                        width="100%",
                    ),
                    on_submit=MyProjectsState.edit_project,
                    reset_on_submit=True,
                ),
                width="100%",
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-xl",
        ),
        open=MyProjectsState.show_edit_modal,
    )

@rx.page(route="/my-projects")
def my_projects_page() -> rx.Component:
    """The my projects page."""
    return rx.box(
        rx.flex(
            sidebar(MyProjectsState),
            # Main content area with flex_grow to take remaining space
            rx.box(
                rx.vstack(
                    # Header section
                    rx.box(
                        rx.hstack(
                            rx.heading("My Projects", size="9", class_name="text-sky-600 font-bold"),
                            rx.spacer(),
                            rx.button(
                                "+ Create new",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="bg-sky-600 text-white hover:bg-sky-500 px-8 py-4 text-xl rounded-lg font-medium"
                            ),
                            width="100%",
                            padding_y="6",
                        ),
                        border_bottom="1px solid",
                        border_color="gray.200",
                        width="100%",
                        margin_bottom="20",
                        padding_x="4",
                    ),
                    # Projects grid section
                    rx.cond(
                        MyProjectsState.has_projects,
                        rx.box(
                            rx.grid(
                                rx.foreach(
                                    MyProjectsState.projects,
                                    show_project
                                ),
                                columns="3",
                                spacing="8",
                                width="100%",
                                padding="8",
                                template_columns="repeat(auto-fit, minmax(450px, 1fr))",
                                gap="8",
                            ),
                            overflow_y="auto",
                            height="calc(100vh - 120px)",
                            padding_x="8",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("You haven't created any projects yet.", class_name="text-white text-lg"),
                            rx.button(
                                "Create Your First Project",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium mt-4",
                            ),
                            spacing="4",
                            height="calc(100vh - 120px)",
                            align="center",
                            justify="center",
                            width="100%",
                        ),
                    ),
                    width="100%",
                    height="100vh",
                ),
                create_project_modal(),
                edit_project_modal(),
                flex_grow="1",  # Makes content take remaining space
                overflow_y="auto",
                padding="20px",
                width="100%",
                class_name="bg-gray-800",  # Added gray background color
            ),
            width="100%",
            height="100vh",
        ),
        width="100%",
        height="100vh",
    )