"""
Django settings for server project.

Generated by 'django-admin startproject' using Django 5.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# IMPORTANT: Uncomment this line to use CustomUser model
AUTH_USER_MODEL = "authen.CustomUser"

# SECURITY WARNING: the secret key used in production secret!
SECRET_KEY = "django-insecure-86$g$4gj_g$7kqd7vmr5n-r&v-m62qtaofqf_t^**k$@24a!1="

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

APPEND_SLASH = False  # Disable appending slashes to URLs

# Application definition
INSTALLED_APPS = [
    "daphne",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "channels",
    "myapp",
    "webcall",
    "authen",
    "communication",
    "message",
    "matches",
    "cloudinary_storage",
    "cloudinary",
    "drf_yasg",  # Added for API documentation
]

ASGI_APPLICATION = "server.asgi.application"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Updated REST Framework settings with the custom authentication
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "authen.authentication.BearerTokenAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

# Updated CORS settings for better frontend integration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

CORS_ALLOW_ALL_ORIGINS = True  # For development - restrict in production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Moved before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "authen.middleware.BearerTokenAuthMiddleware",  # Added custom middleware
    "communication.middleware.CloudinaryConfigMiddleware",
]

ROOT_URLCONF = "server.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "server.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Add Media settings for profile pictures
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Session settings for better security
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"  # Set to 'Strict' in production

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Cloudinary settings
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}


# Use Cloudinary for media storage
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                (
                    os.environ.get("REDIS_HOST", "redis"),
                    int(os.environ.get("REDIS_PORT", 6379)),
                )
            ],
        },
    }
}

# Email settings
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Your App <noreply@yourapp.com>")

RESET_PASSWORD_FRONTEND_URL = os.getenv("RESET_PASSWORD_FRONTEND_URL")

# File upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_EXTENSIONS = {
    "image": ["jpg", "jpeg", "png", "gif"],
    "video": ["mp4", "webm", "mov"],
    "audio": ["mp3", "wav", "ogg"],
    "document": ["pdf", "doc", "docx", "txt"],
}

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Google Cloud WebRTC Settings
# Basic Google STUN server (free public server)
GOOGLE_CLOUD_STUN_SERVER = "stun:stun.l.google.com:19302"

# Google Cloud TURN server settings
GOOGLE_CLOUD_TURN_URL = os.getenv("GOOGLE_CLOUD_TURN_URL", "turn:34.59.164.107:3478")
GOOGLE_CLOUD_TURN_TCP_URL = os.getenv(
    "GOOGLE_CLOUD_TURN_TCP_URL",
    "turn:34.59.164.107:3478?transport=tcp",
)
GOOGLE_CLOUD_TURN_TLS_URL = os.getenv(
    "GOOGLE_CLOUD_TURN_TLS_URL", "turns:34.59.164.107:5349"
)

# In settings.py

# Google Cloud TURN Server Configuration
GOOGLE_CLOUD_TURN_SERVERS = [
    {
        "urls": "turn:34.59.164.107:3478",  # Remove the .com
        "username": os.getenv("GOOGLE_CLOUD_TURN_USERNAME"),
        "credential": os.getenv("GOOGLE_CLOUD_TURN_CREDENTIAL"),
    },
    {
        "urls": "turn:34.59.164.107:3478?transport=tcp",  # Use your actual IP here instead of placeholder
        "username": os.getenv("GOOGLE_CLOUD_TURN_USERNAME"),
        "credential": os.getenv("GOOGLE_CLOUD_TURN_CREDENTIAL"),
    },
    # Optional: Add TLS TURN server
    {
        "urls": "turns:34.59.164.107:5349",  # Use your actual IP here instead of placeholder
        "username": os.getenv("GOOGLE_CLOUD_TURN_USERNAME"),
        "credential": os.getenv("GOOGLE_CLOUD_TURN_CREDENTIAL"),
    },
]

# Update WebRTC config to use these servers
WEBRTC_TURN_SERVERS = GOOGLE_CLOUD_TURN_SERVERS

# For static credentials
GOOGLE_CLOUD_TURN_USERNAME = os.getenv("GOOGLE_CLOUD_TURN_USERNAME", "")
GOOGLE_CLOUD_TURN_CREDENTIAL = os.getenv("GOOGLE_CLOUD_TURN_CREDENTIAL", "")

# For HMAC authentication (recommended for production)
GOOGLE_CLOUD_TURN_SECRET = os.getenv("GOOGLE_CLOUD_TURN_SECRET", "")

# Additional WebRTC settings
WEBRTC_ICE_TIMEOUT = 10000  # ms
WEBRTC_RECONNECTION_ATTEMPTS = 3

# Required for Google Cloud TURN server authorization
SECURE_CROSS_ORIGIN_OPENER_POLICY = os.getenv(
    "SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin-allow-popups"
)

import sys

# Add this at the end of settings.py
if "test" in sys.argv:
    # Use in-memory database for testing
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

    # Use in-memory channel layer instead of Redis
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

    # Disable migrations completely during tests
    class DisableMigrations:
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

    MIGRATION_MODULES = DisableMigrations()
