import reflex as rx
import os
from dotenv import load_dotenv

load_dotenv()

config = rx.Config(
    app_name="Startup_HUB",
    api_url=os.getenv("API_URL", "http://localhost:8000"),
)
