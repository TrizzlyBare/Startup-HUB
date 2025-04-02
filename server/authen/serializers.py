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


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})
