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
                rx.heading(project.name, size="7",border_radius="3xl" , class_name="text-sky-600 w-full font-bold p-2 bg-sky-200 rounded-t-lg font-mono"),
                rx.text(
                    f"->{project.description}",
                    noOfLines=3,
                    size ="4",
                    class_name="text-md px-2 text-gray-500",
                ),
                width="100%",
                padding_x="12",
            ),
            
            # Project details section
            rx.vstack(
                rx.hstack(
                    rx.text(f"Team Size: {project.team_size}",size = "4" ,  class_name=" px-2 text-sky-500 font-bold"),
                    rx.text(f"Stage: {project.funding_stage}",size = "4", class_name="text-md px-2 text-sky-500 font-bold"),
                    spacing="4",
                ),
                rx.text("Tech Stack:", color="black", size = "5", class_name="font-bold mt-2 px-2"),
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
                rx.text("Looking for:", color="black",size = "5", class_name="font-bold mt-2 px-2"),
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
                rx.button(
                    "View Join Requests",
                    on_click=lambda: MyProjectsState.toggle_join_requests_modal(project),
                    class_name="bg-sky-600 text-white hover:bg-sky-700 px-4 py-2 rounded-lg",
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
            rx.dialog.title(
                "Create New Project",
                class_name="text-3xl font-bold mb-4 text-sky-600",
            ),
            rx.dialog.description(
                rx.form(
                    rx.vstack(
                        rx.input(
                            placeholder="Project Name",
                            name="name",
                            required=True,
                            style={"& input::placeholder": {"color": "gray"}},
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        rx.text_area(
                            placeholder="Project Description", 
                            name="description",
                            required=True,
                            height="120px",
                            style={"& textarea::placeholder": {"color": "gray"}},
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        rx.input(
                            placeholder="Tech Stack (comma-separated)",
                            name="tech_stack",
                            style={"& input::placeholder": {"color": "gray"}},
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        rx.select(
                            ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                            placeholder="Funding Stage",
                            name="funding_stage",
                            style={"& select::placeholder": {"color": "gray"}},
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        rx.input(
                            placeholder="Team Size",
                            name="team_size",
                            type="number",
                            min_value=1,
                            style={"& input::placeholder": {"color": "gray"}},
                            default_value="1",
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        rx.input(
                            placeholder="Looking for (comma-separated roles)",
                            style={"& input::placeholder": {"color": "gray"}},
                            name="looking_for",
                            class_name="w-full p-2 border rounded-lg bg-white text-black",
                        ),
                        
                        # Buttons
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg",
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Create Project",
                                    type="submit",
                                    class_name="px-6 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg",
                                ),
                            ),
                            spacing="4",
                            justify="end",
                            width="100%",
                            margin_top="6",
                        ),
                        spacing="6",
                        padding="4",
                    ),
                    on_submit=MyProjectsState.create_project,
                    reset_on_submit=True,
                ),
                width="100%",
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
                class_name="text-3xl font-bold mb-4 text-sky-600",
            ),
            rx.dialog.description(
                rx.vstack(
                    # Error message display
                    rx.cond(
                        MyProjectsState.error,
                        rx.text(
                            MyProjectsState.error,
                            class_name="text-red-500 mb-4 p-2 bg-red-50 rounded-lg",
                        ),
                    ),
                    rx.form(
                        rx.vstack(
                            rx.input(
                                placeholder="Project Name",
                                name="name",
                                required=True,
                                style={"& input::placeholder": {"color": "grey"}},
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
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
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
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
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
                                default_value=MyProjectsState.formatted_tech_stack
                            ),
                            rx.select(
                                ["Pre-seed", "Seed", "Early", "Growth", "Expansion", "Exit"],
                                placeholder="Funding Stage",
                                name="funding_stage",
                                style={"& input::placeholder": {"color": "grey"}},
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
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
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
                                default_value=MyProjectsState.formatted_team_size
                            ),
                            rx.input(
                                placeholder="Looking for (comma-separated roles)",
                                name="looking_for",
                                style={"& input::placeholder": {"color": "grey"}},
                                class_name="w-full p-2 border rounded-lg bg-white text-black",
                                default_value=MyProjectsState.formatted_looking_for
                            ),
                            
                            # Buttons
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
                                width="100%",
                                margin_top="6",
                            ),
                            spacing="6",
                            padding="4",
                        ),
                        on_submit=MyProjectsState.edit_project,
                        reset_on_submit=True,
                    ),
                    width="100%",
                ),
                width="100%",
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
        ),
        open=MyProjectsState.show_edit_modal,
    )

# def join_request_modal() -> rx.Component:
#     """Create join request modal."""
#     return rx.dialog.root(
#         rx.dialog.content(
#             rx.dialog.title(
#                 "Request to Join Project",
#                 class_name="text-3xl font-bold mb-4 text-sky-600",
#             ),
#             rx.dialog.description(
#                 rx.vstack(
#                     # Error message display
#                     rx.cond(
#                         MyProjectsState.error,
#                         rx.text(
#                             MyProjectsState.error,
#                             class_name="text-red-500 mb-4 p-2 bg-red-50 rounded-lg",
#                         ),
#                     ),
#                     rx.text_area(
#                         placeholder="Why do you want to join this project?",
#                         value=MyProjectsState.join_request_message,
#                         on_change=MyProjectsState.set_join_request_message,
#                         height="120px",
#                         class_name="w-full p-2 border rounded-lg bg-white text-black",
#                     ),
#                     rx.hstack(
#                         rx.button(
#                             "Cancel",
#                             on_click=MyProjectsState.toggle_join_requests_modal,
#                             class_name="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg",
#                         ),
#                         rx.button(
#                             "Send Request",
#                             on_click=MyProjectsState.send_join_request,
#                             class_name="px-6 py-2 bg-green-600 text-white hover:bg-green-700 rounded-lg",
#                         ),
#                         spacing="4",
#                         justify="end",
#                         width="100%",
#                         margin_top="6",
#                     ),
#                     spacing="6",
#                     padding="4",
#                 ),
#                 width="100%",
#             ),
#             max_width="600px",
#             width="90vw",
#             class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
#         ),
#         open=MyProjectsState.show_join_requests_modal,
#     )

def join_requests_modal() -> rx.Component:
    """Modal to display join requests for a project."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "Join Requests",
                class_name="text-3xl font-bold mb-4 text-sky-600",
            ),
            rx.dialog.description(
                rx.vstack(
                    # Join requests list
                    rx.cond(
                        MyProjectsState.join_requests,
                        rx.vstack(
                            rx.foreach(
                                MyProjectsState.join_requests,
                                lambda request: rx.box(
                                    rx.vstack(
                                        rx.hstack(
                                            rx.text(
                                                f"From: {request.sender_name}",
                                                class_name="font-bold text-lg",
                                            ),
                                            rx.cond(
                                                request.status == "pending",
                                                rx.text(
                                                    "Status: pending",
                                                    class_name="px-2 py-1 rounded-full text-sm bg-yellow-100 text-yellow-800",
                                                ),
                                                rx.cond(
                                                    request.status == "accepted",
                                                    rx.text(
                                                        "Status: accepted",
                                                        class_name="px-2 py-1 rounded-full text-sm bg-green-100 text-green-800",
                                                    ),
                                                    rx.text(
                                                        "Status: rejected",
                                                        class_name="px-2 py-1 rounded-full text-sm bg-red-100 text-red-800",
                                                    ),
                                                ),
                                            ),
                                            width="100%",
                                            justify="between",
                                        ),
                                        rx.text(
                                            request.message,
                                            class_name="text-gray-600 mt-2",
                                        ),
                                        rx.text(
                                            f"Requested on: {request.created_at.split('T')[0]}",
                                            class_name="text-sm text-gray-500 mt-2",
                                        ),
                                        # Action buttons
                                        rx.hstack(
                                            # Accept/Reject buttons for pending requests
                                            rx.cond(
                                                request.status == "pending",
                                                rx.hstack(
                                                    rx.button(
                                                        "Accept",
                                                        on_click=lambda: [
                                                            MyProjectsState.accept_join_request(request.id, request.sender_id),
                                                            MyProjectsState.delete_join_request(request.id)
                                                        ],
                                                        class_name="bg-green-600 text-white hover:bg-green-700 px-4 py-2 rounded-lg",
                                                    ),
                                                    rx.button(
                                                        "Reject",
                                                        on_click=lambda: MyProjectsState.delete_join_request(request.id),
                                                        class_name="bg-red-600 text-white hover:bg-red-700 px-4 py-2 rounded-lg",
                                                    ),
                                                    spacing="4",
                                                ),
                                            ),
                                            justify="end",
                                            width="100%",
                                            margin_top="2",
                                        ),
                                        class_name="p-4 border border-gray-200 rounded-lg mb-4",
                                    ),
                                ),
                            ),
                        ),
                        rx.text(
                            "No join requests yet.",
                            class_name="text-gray-500 text-center py-4",
                        ),
                    ),
                    # Close button
                    rx.button(
                        "Close",
                        on_click=MyProjectsState.toggle_join_requests_modal,
                        class_name="mt-4 bg-sky-600 text-white hover:bg-sky-700 px-4 py-2 rounded-lg",
                    ),
                    spacing="4",
                    width="100%",
                ),
                width="100%",
            ),
            max_width="600px",
            width="90vw",
            class_name="bg-white p-8 rounded-xl shadow-2xl border border-gray-200",
            style={"position": "fixed", "top": "50%", "left": "50%", "transform": "translate(-50%, -50%)", "zIndex": "1000"},
        ),
        open=MyProjectsState.show_join_requests_modal,
        style={"backgroundColor": "transparent", "& [data-dialog-overlay]": {"background": "transparent"}},
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
                            rx.heading("My Projects", size="9", class_name="text-white font-bold font-serif"),
                            rx.spacer(),
                            rx.button(
                                "+ Create new",
                                on_click=MyProjectsState.toggle_modal,
                                class_name="bg-sky-600 text-cyan-700 bg-cyan-500 hover:bg-cyan-300 px-8 py-4 text-2xl rounded-lg"
                            ),
                            width="100%",
                            padding_y="6",
                        ),
                        border_bottom="3px solid",
                        border_color="#0ea5e9",
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
                # join_request_modal(),
                join_requests_modal(),  # Add the join requests modal
                flex_grow="1",  # Makes content take remaining space
                overflow_y="auto",
                padding="20px",
                width="100%",
                class_name="bg-gray-800",  # Added gray background color
                on_mount=MyProjectsState.load_projects,  # Load projects when the page mounts
            ),
            width="100%",
            height="100vh",
        ),
        width="100%",
        height="100vh",
    )