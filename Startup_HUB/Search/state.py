import reflex as rx
from typing import List

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

    @rx.var
    def formatted_looking_for(self) -> str:
        if self.editing_project:
            return ",".join(self.editing_project.looking_for)
        return ""

    @rx.var
    def formatted_tech_stack(self) -> str:
        if self.editing_project:
            return ",".join(self.editing_project.tech_stack)
        return ""

    @rx.var
    def formatted_team_size(self) -> str:
        if self.editing_project:
            return str(self.editing_project.team_size)
        return "1"

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