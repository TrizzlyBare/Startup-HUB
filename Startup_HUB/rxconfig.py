import reflex as rx

config = rx.Config(
    app_name="Startup_HUB",
    db_url="sqlite:///reflex.db",
    env=rx.Env.DEV,
    telemetry_enabled=False,
    # Specify only the routes we want to include
    frontend_path="Startup_HUB/frontend",
    api_url=None,
) 