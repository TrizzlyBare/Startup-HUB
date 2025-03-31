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
    created_at: str = "2024-01-01"

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
            created_at="2024-03-01",
        ),
        Project(
            name="Eco Platform", 
            description="Sustainable delivery platform.",
            tech_stack=["React", "Node.js", "MongoDB"],
            funding_stage="Seed",
            team_size=3,
            looking_for=["Full Stack", "UI/UX"],
            created_at="2024-02-15",
        ),
    ]
    new_project: Project = Project(name="", description="")
    show_modal: bool = False
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
                    created_at="2024-03-01",  # You might want to use actual date
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
            rx.heading(project.name, size="3", class_name="text-sky-600 font-bold"),
            rx.text(
                project.description,
                color="black",
                noOfLines=3,
                class_name="text-lg font-small",
            ),
            rx.text(f"Created: {project.created_at}", color="gray.600", class_name="text-sm"),
            rx.hstack(
                rx.text(f"Team Size: {project.team_size}", color="black", class_name="text-md"),
                rx.text(f"Stage: {project.funding_stage}", color="black", class_name="text-md"),
                spacing="4",
            ),
            rx.text("Tech Stack:", color="black", class_name="text-md font-medium mt-2"),
            rx.hstack(
                rx.foreach(
                    project.tech_stack,
                    lambda tech: rx.box(
                        tech,
                        class_name="bg-sky-100 text-sky-700 px-3 py-1 rounded-full m-1",
                    ),
                ),
                wrap="wrap",
            ),
            rx.text("Looking for:", color="black", class_name="text-md font-medium mt-2"),
            rx.hstack(
                rx.foreach(
                    project.looking_for,
                    lambda role: rx.box(
                        role,
                        class_name="bg-green-100 text-green-700 px-3 py-1 rounded-full m-1",
                    ),
                ),
                wrap="wrap",
            ),
            rx.hstack(
                rx.spacer(),
                rx.button(
                    "Edit",
                    class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium",
                ),
                rx.button(
                    "Delete",
                    on_click=lambda: MyProjectsState.delete_project(project.name),
                    class_name="bg-red-600 text-white hover:bg-red-700 px-6 py-2 rounded-lg font-medium",
                ),
                spacing="4",
                width="100%",
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

def create_project_modal() -> rx.Component:
    """Create project modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Create New Project",
                class_name="text-2xl font-bold text-sky-600",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        rx.input(
                            placeholder="Project Name",
                            name="name",
                            required=True
                        ),
                        rx.text_area(
                            placeholder="Project Description", 
                            name="description",
                            required=True
                        ),
                        rx.input(
                            placeholder="Tech Stack (comma-separated)",
                            name="tech_stack",
                        ),
                        rx.select(
                            ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                            placeholder="Funding Stage",
                            name="funding_stage",
                        ),
                        rx.input(
                            placeholder="Team Size",
                            name="team_size",
                            type="number",
                            min_value=1,
                            default_value="1",
                        ),
                        rx.input(
                            placeholder="Looking for (comma-separated roles)",
                            name="looking_for",
                        ),
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="bg-red-600 text-white hover:bg-red-700",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Create",
                                    type="submit",
                                    class_name="bg-sky-600 text-white hover:bg-sky-700",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                        ),
                        spacing="4",
                    ),
                    on_submit=MyProjectsState.create_project,
                    reset_on_submit=True,
                ),
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-xl",
        ),
        open=MyProjectsState.show_modal,
    )

@rx.page(route="/my-projects")
def my_projects_page() -> rx.Component:
    """The my projects page."""
    return rx.box(
        rx.hstack(
            sidebar(MyProjectsState),
            # Main content area
            rx.box(
                rx.container(
                    rx.vstack(
                        # Header section
                        rx.box(
                            rx.hstack(
                                rx.heading("My Projects", size="3", class_name="text-sky-600 font-bold"),
                                rx.spacer(),
                                rx.button(
                                    "Create New Project",
                                    on_click=MyProjectsState.toggle_modal,
                                    class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium",
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
                                    columns="2",
                                    spacing="8",
                                    width="100%",
                                    padding="8",
                                    template_columns="repeat(auto-fit, minmax(450px, 1fr))",
                                ),
                                overflow_y="auto",
                                height="calc(100vh - 120px)",
                                padding_x="4",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.text("You haven't created any projects yet.", class_name="text-gray-600 text-lg"),
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
                        spacing="0",
                        width="100%",
                        height="100vh",
                        padding_x="4",
                    ),
                    max_width="100%",
                    width="100%",
                    height="100%",
                    padding_x="4",
                    padding_y="2",
                ),
                create_project_modal(),
                width="100%",
                overflow="hidden",
                background="gray.50",
            ),
            spacing="0",
            align="stretch",
            width="100%",
            height="100vh",
            overflow="hidden",
        ),
        width="100%",
        height="100vh",
        overflow="hidden",
    )