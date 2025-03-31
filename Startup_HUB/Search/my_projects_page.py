import reflex as rx
from typing import List
from .state import MyProjectsState, Project
from ..Matcher.SideBar import sidebar  # Keep your original import

def show_project(project: rx.Var[Project]) -> rx.Component:
    """Show a project component."""
    return rx.box(
        rx.vstack(
            # Project header and description section
            rx.vstack(
                rx.heading(project.name, size="3", class_name="text-sky-600 font-bold"),
                rx.text(
                    project.description,
                    color="black",
                    noOfLines=3,
                    class_name="text-lg font-small",
                ),
                align_items="start",
                width="100%",
            ),
            
            # Project details section
            rx.vstack(
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
                align_items="start",
                width="100%",
            ),
            
            # Buttons section - fixed at bottom
            rx.spacer(),  # This pushes the buttons to the bottom
            rx.hstack(
                rx.button(
                    "Edit",
                    on_click=lambda: MyProjectsState.start_edit(project),
                    class_name="bg-sky-600 text-white hover:bg-sky-700 px-6 py-2 rounded-lg font-medium",
                ),
                rx.button(
                    "Delete",
                    on_click=lambda: MyProjectsState.delete_project(project.name),
                    class_name="bg-red-600 text-white hover:bg-red-700 px-6 py-2 rounded-lg font-medium",
                ),
                spacing="4",
                width="100%",
                justify="end",
            ),
            height="100%",  # Make the vstack take full height
            align_items="stretch",  # Stretch children to full width
            spacing="4",
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
                class_name="text-3xl font-bold mb-4 text-blue-600",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        rx.input(
                            placeholder="Project Name",
                            name="name",
                            required=True,
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        rx.text_area(
                            placeholder="Project Description", 
                            name="description",
                            required=True,
                            height="120px",
                            style={"& textarea::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        rx.input(
                            placeholder="Tech Stack (comma-separated)",
                            name="tech_stack",
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        rx.select(
                            ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                            placeholder="Funding Stage",
                            name="funding_stage",
                            style={"& select::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        rx.input(
                            placeholder="Team Size",
                            name="team_size",
                            type="number",
                            min_value=1,
                            style={"& input::placeholder": {"color": "grey"}},
                            default_value="1",
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        rx.input(
                            placeholder="Looking for (comma-separated roles)",
                            style={"& input::placeholder": {"color": "grey"}},
                            name="looking_for",
                            class_name="w-full p-2 border rounded-lg bg-white",
                        ),
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Create",
                                    type="submit",
                                    class_name="px-6 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                        ),
                        spacing="6",
                        padding="4",
                    ),
                    on_submit=MyProjectsState.create_project,
                    reset_on_submit=True,
                ),
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=MyProjectsState.show_modal,
    )

def edit_project_modal() -> rx.Component:
    """Edit project modal."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Edit Project", 
                class_name="text-3xl font-bold mb-4",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        rx.input(
                            placeholder="Project Name",
                            name="name",
                            required=True,
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                            default_value=rx.cond(
                                MyProjectsState.editing_project,
                                MyProjectsState.editing_project.name,
                                ""
                            ),
                        ),
                        rx.text_area(
                            placeholder="Project Description", 
                            name="description",
                            required=True,
                            height="120px",
                            style={"& textarea::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                            default_value=rx.cond(
                                MyProjectsState.editing_project,
                                MyProjectsState.editing_project.description,
                                ""
                            ),
                        ),
                        rx.input(
                            placeholder="Tech Stack (comma-separated)",
                            name="tech_stack",
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                            default_value=MyProjectsState.formatted_tech_stack
                        ),
                        rx.select(
                            ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                            placeholder="Funding Stage",
                            name="funding_stage",
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                            default_value=rx.cond(
                                MyProjectsState.editing_project,
                                MyProjectsState.editing_project.funding_stage,
                                "Pre-seed"
                            ),
                        ),
                        rx.input(
                            placeholder="Team Size",
                            name="team_size",
                            type="number",
                            min_value=1,
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                            default_value=MyProjectsState.formatted_team_size
                        ),
                        rx.input(
                            placeholder="Looking for (comma-separated roles)",
                            name="looking_for",
                            style={"& input::placeholder": {"color": "grey"}},
                            class_name="w-full p-2 border rounded-lg bg-white",
                            default_value=MyProjectsState.formatted_looking_for
                        ),
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                variant="soft",
                                color_scheme="gray",
                                on_click=MyProjectsState.toggle_edit_modal,
                                class_name="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Changes",
                                    type="submit",
                                    class_name="px-6 py-2 bg-sky-600 text-white hover:bg-sky-700 rounded-lg",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                        ),
                        spacing="6",
                        padding="4",
                    ),
                    on_submit=MyProjectsState.edit_project,
                    reset_on_submit=True,
                ),
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
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
                                columns="3",
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
                    width="100%",
                    height="100vh",
                ),
                create_project_modal(),
                edit_project_modal(),
                flex_grow="1",  # Makes content take remaining space
                overflow_y="auto",
                padding="20px",
                width="100%",
            ),
            width="100%",
            height="100vh",
        ),
        width="100%",
        height="100vh",
    )