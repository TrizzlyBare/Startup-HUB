import reflex as rx

class MatchState(rx.State):
    """The app state."""
    active_tab: str = "Matches"
    selected_issue_type: str = ""

    def set_active_tab(self, tab: str):
        """Set the active tab."""
        self.active_tab = tab

    def set_selected_issue_type(self, issue_type: str):
        """Set the selected issue type."""
        self.selected_issue_type = issue_type 