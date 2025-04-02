from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser
from cloudinary.utils import cloudinary_url


class UserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

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
        # Use Django's password validation
        validate_password(value)
        return value

    def create(self, validated_data):
        # Remove profile picture from validated_data if it's None
        profile_picture = validated_data.pop("profile_picture", None)

        # Create user with required fields
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

    def update(self, instance, validated_data):
        # Handle password separately
        if "password" in validated_data:
            password = validated_data.pop("password")
            instance.set_password(password)

        # Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class UserInfoSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["id"]
