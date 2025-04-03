from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser, ContactLink
from cloudinary.utils import cloudinary_url


class ContactLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactLink
        fields = ["id", "title", "url"]


class UserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()
    contact_links = ContactLinkSerializer(many=True, read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "profile_picture",
            "profile_picture_url",
            "bio",
            "contact_links",
        ]
        extra_kwargs = {
            "password": {"write_only": True},
            "profile_picture": {"write_only": True},
            "username": {"required": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
            "bio": {"required": True},
        }

    def get_profile_picture_url(self, obj):
        """Get the Cloudinary URL for the profile picture"""
        if obj.profile_picture:
            return obj.profile_picture.url
        return None

    def validate_password(self, value):
        """Validate the password using Django's built-in password validators"""
        validate_password(value)
        return value

    def create(self, validated_data):
        """Create a new user instance with the validated data"""
        profile_picture = validated_data.pop("profile_picture", None)

        # Create the user with the required fields
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            bio=validated_data["bio"],
        )

        # Add optional fields if they exist
        if profile_picture:
            user.profile_picture = profile_picture

        user.save()
        return user


class UserInfoSerializer(serializers.ModelSerializer):
    contact_links = ContactLinkSerializer(many=True, required=False)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "profile_picture",
            "bio",
            "industry",
            "experience",
            "skills",
            "contact_links",
        ]
        read_only_fields = ["id"]

    def update(self, instance, validated_data):
        """Handle nested contact links update"""
        contact_links_data = validated_data.pop("contact_links", None)

        # Update the user instance with the remaining validated data
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update contact links if provided
        if contact_links_data is not None:
            # Remove existing contact links and create new ones
            instance.contact_links.all().delete()
            for link_data in contact_links_data:
                ContactLink.objects.create(user=instance, **link_data)

        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})
