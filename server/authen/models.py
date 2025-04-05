from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField


class ContactLink(models.Model):
    """Model to store contact links for users"""

    user = models.ForeignKey(
        "CustomUser", related_name="contact_links", on_delete=models.CASCADE
    )
    title = models.CharField(
        max_length=100, help_text="Link title (e.g., LinkedIn, GitHub)"
    )
    url = models.URLField(help_text="URL to contact resource")

    def __str__(self):
        return f"{self.title}: {self.url}"


class CustomUser(AbstractUser):
    """
    Extended User model with additional professional and personal information
    """

    email = models.EmailField(unique=True)

    profile_picture = CloudinaryField(
        "profile_picture",
        folder="startup_hub/profile_pics",
        blank=True,
        null=True,
        transformation={"width": 500, "height": 500, "crop": "fill", "gravity": "face"},
    )

    bio = models.TextField(
        "bio",
        max_length=500,
        blank=True,
        null=True,
        help_text="A short description about yourself",
    )

    # Professional fields
    industry = models.CharField(
        "industry",
        max_length=100,
        blank=True,
        null=True,
        help_text="Your industry or sector",
    )

    experience = models.CharField(
        "experience",
        max_length=50,
        blank=True,
        null=True,
        help_text="Your years of experience",
    )

    skills = models.TextField(
        "skills", blank=True, null=True, help_text="Comma-separated list of your skills"
    )

    past_projects = models.TextField(
        "past_projects",
        blank=True,
        null=True,
        help_text="Comma-separated list of past projects",
    )

    career_summary = models.TextField(
        "career_summary",
        blank=True,
        null=True,
        help_text="A brief overview of your professional journey and career goals",
    )

    # Customize related names to avoid conflicts
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="custom_user_set",
        related_query_name="custom_user",
    )

    def __str__(self):
        return self.username


class ContactLink(models.Model):
    user = models.ForeignKey(
        "CustomUser", related_name="contact_links", on_delete=models.CASCADE
    )
    title = models.CharField(
        max_length=100, help_text="Link title (e.g., LinkedIn, GitHub)"
    )
    url = models.URLField(help_text="URL to contact resource")
