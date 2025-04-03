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


class PastProject(models.Model):
    """
    Model to store past projects for users
    """

    PROJECT_STATUS_CHOICES = [
        ("completed", "Completed"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
    ]

    user = models.ForeignKey(
        CustomUser, related_name="past_projects", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200, help_text="Project title or name")
    description = models.TextField(help_text="Detailed description of the project")
    start_date = models.DateField(null=True, blank=True, help_text="Project start date")
    end_date = models.DateField(null=True, blank=True, help_text="Project end date")
    status = models.CharField(
        max_length=20,
        choices=PROJECT_STATUS_CHOICES,
        default="completed",
        help_text="Current status of the project",
    )
    technologies = models.TextField(
        blank=True,
        null=True,
        help_text="Technologies or tools used in the project (comma-separated)",
    )
    project_link = models.URLField(
        blank=True, null=True, help_text="Link to project repository or live demo"
    )
    role = models.CharField(
        max_length=100, blank=True, null=True, help_text="Your role in the project"
    )

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    class Meta:
        ordering = ["-end_date", "-start_date"]
        verbose_name_plural = "Past Projects"
