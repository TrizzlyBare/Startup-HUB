import reflex as rx
from pathlib import Path
import json
from typing import List, Dict, Optional

# State class to manage the search state
class SearchState(rx.State):
    """The search state."""
    search_query: str = ""
    selected_industry: str = "All"
    selected_location: str = "All"
    startup_groups: List[Dict] = []
    filtered_groups: List[Dict] = []
    industries: List[str] = []
    locations: List[str] = []
    selected_group: Optional[Dict] = None

    def load_startup_groups(self):
        """Load startup groups data from JSON file."""
        try:
            with open(Path("Startup_HUB/Data/startup_groups.json"), 'r', encoding='utf-8') as f:
                self.startup_groups = json.load(f)
                # Extract unique industries and locations
                self.industries = sorted(list(set(
                    group.get('industry', '') 
                    for group in self.startup_groups 
                    if group.get('industry')
                )))
                self.locations = sorted(list(set(
                    group.get('location', '') 
                    for group in self.startup_groups 
                    if group.get('location')
                )))
                self.filtered_groups = self.startup_groups
        except FileNotFoundError:
            self.startup_groups = []
            self.filtered_groups = []

    def search_groups(self):
        """Search groups based on query and filters."""
        if not self.search_query:
            self.filtered_groups = self.startup_groups
            return

        query = self.search_query.lower()
        results = []

        for group in self.startup_groups:
            # Check if group matches search criteria
            name_match = query in group.get('name', '').lower()
            description_match = query in group.get('description', '').lower()
            industry_match = query in group.get('industry', '').lower()

            # Apply filters
            if self.selected_industry != "All" and group.get('industry') != self.selected_industry:
                continue

            if self.selected_location != "All" and group.get('location') != self.selected_location:
                continue

            if name_match or description_match or industry_match:
                results.append(group)

        self.filtered_groups = results

    def select_group(self, group: Dict):
        """Select a group to view details."""
        self.selected_group = group

    def clear_selection(self):
        """Clear the selected group."""
        self.selected_group = None

def group_card(group: Dict) -> rx.Component:
    """Create a card component for a startup group."""
    return rx.box(
        rx.vstack(
            rx.heading(group.get('name', 'Unnamed Group'), size="md"),
            rx.text(f"Industry: {group.get('industry', 'N/A')}"),
            rx.text(f"Location: {group.get('location', 'N/A')}"),
            rx.text(f"Members: {len(group.get('members', []))}"),
            rx.text(group.get('description', 'No description available.')),
            rx.button(
                "View Details",
                on_click=lambda: SearchState.select_group(group),
                color_scheme="red",
                size="sm",
            ),
            spacing="4",
            padding="4",
            border="1px solid #eaeaea",
            border_radius="lg",
            width="100%",
        ),
        width="100%",
    )

def search_page() -> rx.Component:
    """The search page component."""
    return rx.vstack(
        rx.heading("🔍 Search Startup Groups", size="lg", mb="8"),
        
        # Search and filters section
        rx.hstack(
            rx.input(
                placeholder="Search startup groups...",
                value=SearchState.search_query,
                on_change=SearchState.set_search_query,
                width="60%",
                size="lg",
            ),
            rx.select(
                ["All"] + SearchState.industries,
                value=SearchState.selected_industry,
                on_change=SearchState.set_selected_industry,
                placeholder="Select Industry",
                width="20%",
            ),
            rx.select(
                ["All"] + SearchState.locations,
                value=SearchState.selected_location,
                on_change=SearchState.set_selected_location,
                placeholder="Select Location",
                width="20%",
            ),
            spacing="4",
            width="100%",
            mb="8",
        ),
        
        # Search button
        rx.button(
            "Search",
            on_click=SearchState.search_groups,
            color_scheme="red",
            size="lg",
            mb="8",
        ),
        
        # Results section
        rx.cond(
            len(SearchState.filtered_groups) == 0,
            rx.text("No startup groups found matching your criteria."),
            rx.wrap(
                *[group_card(group) for group in SearchState.filtered_groups],
                spacing="4",
                justify="center",
            ),
        ),
        
        # Modal for group details
        rx.modal(
            rx.modal_overlay(
                rx.modal_content(
                    rx.modal_header(SearchState.selected_group.get('name', 'Group Details') if SearchState.selected_group else ''),
                    rx.modal_close_button(),
                    rx.modal_body(
                        rx.vstack(
                            rx.text(f"Industry: {SearchState.selected_group.get('industry', 'N/A')}"),
                            rx.text(f"Location: {SearchState.selected_group.get('location', 'N/A')}"),
                            rx.text(f"Members: {len(SearchState.selected_group.get('members', []))}"),
                            rx.text(SearchState.selected_group.get('description', 'No description available.')),
                            spacing="4",
                        ) if SearchState.selected_group else rx.text("No details available."),
                    ),
                    rx.modal_footer(
                        rx.button("Close", on_click=SearchState.clear_selection),
                    ),
                ),
            ),
            is_open=SearchState.selected_group is not None,
            on_close=SearchState.clear_selection,
        ),
        
        spacing="8",
        padding="8",
        width="100%",
        max_width="1200px",
        margin="0 auto",
    ) 