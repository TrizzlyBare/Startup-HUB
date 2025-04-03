from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import StartupIdea, StartupImage
import tempfile
from PIL import Image
import json
import io

User = get_user_model()


class StartupIdeaModelTests(TestCase):
    """Test cases for the StartupIdea model"""

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            skills="Python, Django, React",
            industry="Technology",
        )

        # Create a test startup idea
        self.startup_idea = StartupIdea.objects.create(
            user=self.user,
            name="Test Startup",
            stage="IDEA",
            user_role="FOUNDER",
            pitch="A test startup idea",
            description="This is a detailed description of the test startup",
            skills="Python, Django, React",
            looking_for="Designer, Marketer",
            website="https://teststartup.com",
            funding_stage="Pre-seed",
            investment_needed=10000.00,
        )

    def test_string_representation(self):
        """Test the string representation of a StartupIdea"""
        self.assertEqual(str(self.startup_idea), "testuser's Idea - Test Startup")

    def test_properties(self):
        """Test the property methods that convert strings to lists"""
        # Test skills_list property
        self.assertEqual(self.startup_idea.skills_list, ["Python", "Django", "React"])

        # Test looking_for_list property
        self.assertEqual(self.startup_idea.looking_for_list, ["Designer", "Marketer"])

        # Test with empty fields
        empty_idea = StartupIdea.objects.create(
            user=self.user,
            name="Empty Fields",
            skills="",
            looking_for="",
        )
        self.assertEqual(empty_idea.skills_list, [])
        self.assertEqual(empty_idea.looking_for_list, [])

    def test_member_count_property(self):
        """Test the member_count property"""
        # Create additional test users
        member1 = User.objects.create_user(
            username="member1",
            email="member1@example.com",
            password="password123",
        )

        member2 = User.objects.create_user(
            username="member2",
            email="member2@example.com",
            password="password123",
        )

        # Initial count should be 1 (just the owner)
        self.assertEqual(self.startup_idea.member_count, 1)

        # Add members and check count
        self.startup_idea.members.add(member1)
        self.assertEqual(self.startup_idea.member_count, 2)

        self.startup_idea.members.add(member2)
        self.assertEqual(self.startup_idea.member_count, 3)

        # If owner is also in the members list, count should remain the same
        self
