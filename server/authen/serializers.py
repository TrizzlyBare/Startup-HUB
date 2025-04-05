from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, ContactLink
from cloudinary.utils import cloudinary_url


class ContactLinkSerializer(serializers.ModelSerializer):
    """
    Serializer for contact links with validation
    """

    class Meta:
        model = ContactLink
        fields = ["id", "title", "url"]
        read_only_fields = ["id"]

    def validate_url(self, value):
        """
        Validate that the URL is a valid web address
        """
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError

        url_validator = URLValidator()
        try:
            url_validator(value)
        except ValidationError:
            raise serializers.ValidationError("Enter a valid URL.")
        return value

    def validate_title(self, value):
        """
        Validate the title
        """
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        if len(value) > 100:
            raise serializers.ValidationError(
                "Title cannot be longer than 100 characters."
            )
        return value


class BaseUserSerializer(serializers.ModelSerializer):
    """Base serializer with common user fields"""

    profile_picture_url = serializers.SerializerMethodField()
    contact_links = serializers.SerializerMethodField()
    skills_list = serializers.SerializerMethodField()
    past_projects_list = serializers.SerializerMethodField()

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
            "skills_list",
            "past_projects",
            "past_projects_list",
            "career_summary",
            "contact_links",
        ]

    def get_profile_picture_url(self, obj):
        """Get the Cloudinary URL for the profile picture with error handling"""
        if obj.profile_picture and obj.profile_picture.public_id:
            try:
                return obj.profile_picture.url
            except ValueError:
                # Return None when Cloudinary is not configured properly
                return None
        return None

    def get_skills_list(self, obj):
        """
        Get skills as a list
        """
        if not obj.skills:
            return []
        return [skill.strip() for skill in obj.skills.split(",") if skill.strip()]

    def get_past_projects_list(self, obj):
        """
        Get past projects as a list
        """
        if not obj.past_projects:
            return []
        return [
            project.strip()
            for project in obj.past_projects.split(",")
            if project.strip()
        ]


class UserInfoSerializer(BaseUserSerializer):
    """
    Serializer for user information with read-only access
    """

    class Meta(BaseUserSerializer.Meta):
        read_only_fields = ["id", "email"]

    def get_contact_links(self, obj):
        """Get serialized contact links"""
        return ContactLinkSerializer(obj.contact_links.all(), many=True).data

    def get_profile_picture_url(self, obj):
        """Get the Cloudinary URL for the profile picture with error handling"""
        if obj.profile_picture and obj.profile_picture.public_id:
            try:
                return obj.profile_picture.url
            except ValueError:
                # Return None when Cloudinary is not configured properly
                return None
        return None

    def get_skills_list(self, obj):
        """
        Get skills as a list
        """
        if not obj.skills:
            return []
        return [skill.strip() for skill in obj.skills.split(",") if skill.strip()]

    def get_past_projects_list(self, obj):
        """
        Get past projects as a list
        """
        if not obj.past_projects:
            return []
        return [
            project.strip()
            for project in obj.past_projects.split(",")
            if project.strip()
        ]


class UserSerializer(BaseUserSerializer):
    contact_links = ContactLinkSerializer(many=True, required=False)
    password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + ["password", "contact_links"]
        extra_kwargs = {
            "password": {"write_only": True},
            "profile_picture": {"write_only": True},
            "username": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def create(self, validated_data):
        # Extract contact links data
        contact_links_data = validated_data.pop("contact_links", [])

        # Create user
        password = validated_data.pop("password", None)
        user = CustomUser(**validated_data)

        # Set password if provided
        if password:
            user.set_password(password)

        # Save user
        user.save()

        # Add contact links
        for link_data in contact_links_data:
            ContactLink.objects.create(user=user, **link_data)

        return user

    def update(self, instance, validated_data):
        # Extract contact links data
        contact_links_data = validated_data.pop("contact_links", None)

        # Update standard fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update password if provided
        if "password" in validated_data:
            instance.set_password(validated_data["password"])

        # Save the instance
        instance.save()

        # Update contact links if provided
        if contact_links_data is not None:
            # Remove existing contact links
            instance.contact_links.all().delete()

            # Add new contact links
            for link_data in contact_links_data:
                ContactLink.objects.create(user=instance, **link_data)

        return instance

    get_profile_picture_url = BaseUserSerializer.get_profile_picture_url
    get_skills_list = BaseUserSerializer.get_skills_list
    get_past_projects_list = BaseUserSerializer.get_past_projects_list

    def validate_skills(self, value):
        """
        Validate skills input
        """
        if value:
            # Ensure it's a comma-separated string
            if not isinstance(value, str):
                raise serializers.ValidationError(
                    "Skills must be a comma-separated string"
                )
        return value

    def validate_past_projects(self, value):
        """
        Validate past projects input
        """
        if value:
            # Ensure it's a comma-separated string
            if not isinstance(value, str):
                raise serializers.ValidationError(
                    "Past projects must be a comma-separated string"
                )
        return value

    def create(self, validated_data):
        """
        Create a new user with optional skills, past projects, and contact links
        """
        # Extract nested data
        contact_links_data = validated_data.pop("contact_links", [])
        past_projects = validated_data.pop("past_projects", None)
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

        # Add past projects
        if past_projects:
            user.past_projects = past_projects
            user.save()

        # Add contact links
        for link_data in contact_links_data:
            ContactLink.objects.create(user=user, **link_data)

        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset"""

    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a password reset"""

    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, style={"input_type": "password"}
    )

    def validate_new_password(self, value):
        """
        Validate the new password using Django's password validators
        """
        validate_password(value)
        return value
