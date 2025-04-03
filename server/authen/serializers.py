from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, ContactLink, PastProject
from cloudinary.utils import cloudinary_url


class ContactLinkSerializer(serializers.ModelSerializer):
    """Serializer for contact links"""

    class Meta:
        model = ContactLink
        fields = ["id", "title", "url"]


class PastProjectSerializer(serializers.ModelSerializer):
    """Serializer for past projects"""

    class Meta:
        model = PastProject
        fields = [
            "id",
            "title",
            "description",
            "start_date",
            "end_date",
            "status",
            "technologies",
            "project_link",
            "role",
        ]

    def validate(self, data):
        """
        Validate project dates
        """
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("End date must be after start date")

        return data


class BaseUserSerializer(serializers.ModelSerializer):
    """Base serializer with common user fields"""

    profile_picture_url = serializers.SerializerMethodField()
    contact_links = serializers.SerializerMethodField()
    past_projects = PastProjectSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "profile_picture",
            "profile_picture_url",
            "bio",
            "industry",
            "experience",
            "skills",
            "career_summary",
            "contact_links",
            "past_projects",
        ]

    def get_contact_links(self, obj):
        """Get serialized contact links"""
        return ContactLinkSerializer(obj.contact_links.all(), many=True).data

    def get_profile_picture_url(self, obj):
        """Get the Cloudinary URL for the profile picture"""
        if obj.profile_picture:
            return obj.profile_picture.url
        return None


class UserInfoSerializer(BaseUserSerializer):
    """
    Serializer for user information with read-only access
    """

    class Meta(BaseUserSerializer.Meta):
        read_only_fields = ["id", "email"]


class UserSerializer(BaseUserSerializer):
    """
    Full user serializer with write access to all fields
    """

    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )
    contact_links = ContactLinkSerializer(many=True, required=False)
    past_projects = PastProjectSerializer(many=True, required=False)

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + ["password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "profile_picture": {"write_only": True},
            "username": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def validate_username(self, value):
        """Validate that the username is unique"""
        # Check if this is an update or create operation
        instance = getattr(self, "instance", None)

        # If updating, allow the current username
        if instance and instance.username == value:
            return value

        # Check for existing username
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username is already in use. Please choose a different one."
            )
        return value

    def validate_password(self, value):
        """Validate the password using Django's built-in password validators"""
        if value:
            validate_password(value)
        return value

    def create(self, validated_data):
        """
        Create a new user with optional past projects and contact links
        """
        # Extract nested data
        contact_links_data = validated_data.pop("contact_links", [])
        past_projects_data = validated_data.pop("past_projects", [])
        profile_picture = validated_data.pop("profile_picture", None)

        # Create user
        password = validated_data.pop("password", None)
        user = CustomUser(**validated_data)

        # Set password if provided
        if password:
            user.set_password(password)

        # Save user
        user.save()

        # Add profile picture
        if profile_picture:
            user.profile_picture = profile_picture
            user.save()

        # Add contact links
        for link_data in contact_links_data:
            ContactLink.objects.create(user=user, **link_data)

        # Add past projects
        for project_data in past_projects_data:
            PastProject.objects.create(user=user, **project_data)

        return user

    def update(self, instance, validated_data):
        """
        Update user with optional past projects and contact links
        """
        # Extract nested data
        contact_links_data = validated_data.pop("contact_links", None)
        past_projects_data = validated_data.pop("past_projects", None)
        password = validated_data.pop("password", None)
        profile_picture = validated_data.pop("profile_picture", None)

        # Update standard fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update password if provided
        if password:
            instance.set_password(password)

        # Update profile picture
        if profile_picture:
            instance.profile_picture = profile_picture

        # Save the instance
        instance.save()

        # Update contact links if provided
        if contact_links_data is not None:
            # Remove existing contact links
            instance.contact_links.all().delete()
            for link_data in contact_links_data:
                ContactLink.objects.create(user=instance, **link_data)

        # Update past projects if provided
        if past_projects_data is not None:
            # Remove existing past projects
            instance.past_projects.all().delete()
            for project_data in past_projects_data:
                PastProject.objects.create(user=instance, **project_data)

        return instance


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})
