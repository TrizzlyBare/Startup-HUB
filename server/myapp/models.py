from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

# Create your models here.

class StartupProfile(models.Model):
    ROLE_CHOICES = [
        ('FOUNDER', 'Founder'),
        ('CO_FOUNDER', 'Co-Founder'),
        ('DEVELOPER', 'Developer'),
        ('DESIGNER', 'Designer'),
        ('MARKETER', 'Marketing Specialist'),
        ('BUSINESS_DEV', 'Business Developer'),
        ('PRODUCT_MANAGER', 'Product Manager'),
        ('FINANCIAL_EXPERT', 'Financial Expert'),
        ('OTHER', 'Other'),
    ]

    STAGE_CHOICES = [
        ('IDEA', 'Idea Stage'),
        ('MVP', 'MVP'),
        ('EARLY', 'Early Stage'),
        ('GROWTH', 'Growth Stage'),
        ('SCALING', 'Scaling'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='startup_profile'
    )
    
    # Startup Details
    startup_name = models.CharField(max_length=100, blank=True)
    startup_stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default='IDEA'
    )
    pitch = models.TextField(max_length=500, help_text="Elevator pitch for your startup idea")
    description = models.TextField(help_text="Detailed description of your startup")
    
    # Role and Skills
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    skills = models.JSONField(default=list, help_text="List of skills and expertise")
    looking_for = models.JSONField(
        default=list,
        help_text="Roles/skills you're looking for in potential co-founders"
    )
    
    # Pictures (Multiple startup-related images)
    pitch_deck = CloudinaryField(
        'pitch_deck',
        folder='startup_hub/pitch_decks',
        blank=True,
        null=True,
        resource_type='auto'
    )
    startup_images = models.JSONField(
        default=list,
        help_text="List of Cloudinary URLs for startup images"
    )
    
    # Additional Info
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    funding_stage = models.CharField(max_length=100, blank=True)
    investment_needed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # User Profile Fields
    bio = models.TextField(max_length=500, blank=True, help_text="Tell others about yourself")
    age = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    interests = models.JSONField(
        default=list,
        help_text="List of personal and professional interests"
    )
    
    # Additional profile images (like Tinder's multiple photos)
    profile_images = models.JSONField(
        default=list,
        help_text="List of Cloudinary URLs for profile images"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Startup Profile - {self.startup_name}"

    class Meta:
        ordering = ['-created_at']

class StartupImage(models.Model):
    profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = CloudinaryField(
        'startup_image',
        folder='startup_hub/startup_images',
        transformation={
            'width': 800,
            'height': 600,
            'crop': 'fill'
        }
    )
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.profile.startup_name}"
