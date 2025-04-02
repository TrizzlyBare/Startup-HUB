import os
from dotenv import load_dotenv
import reflex as rx

# Load environment variables from .env file
load_dotenv()

config = rx.Config(
    app_name="Startup_HUB",
    server_url=os.getenv("SERVER_URL")  # Use the environment variable
)