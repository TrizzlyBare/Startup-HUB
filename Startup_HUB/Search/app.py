import reflex as rx
from .search_page import search_page, SearchState

# Initialize the app
app = rx.App()

# Add the search page to the app
app.add_page(
    search_page,
    title="Startup Group Search",
    description="Search and discover startup groups",
    on_load=SearchState.load_startup_groups,
)

# Run the app
if __name__ == "__main__":
    app.compile() 