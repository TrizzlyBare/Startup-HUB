from rest_framework import serializers
from .models import StartupIdea, StartupImage
from django.contrib.auth import get_user_model

# Get the CustomUser model
CustomUser = get_user_model()


class StartupImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = StartupImage
        fields = ["id", "image", "image_url", "caption", "created_at"]
        extra_kwargs = {"image": {"write_only": True}}

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class StartupIdeaSerializer(serializers.ModelSerializer):
    images = StartupImageSerializer(many=True, read_only=True)
    pitch_deck_url = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)
    user_profile_picture = serializers.SerializerMethodField(read_only=True)
    user_role_display = serializers.CharField(
        source="get_user_role_display", read_only=True
    )
    looking_for_list = serializers.SerializerMethodField()
    skills_list = serializers.SerializerMethodField()

    class Meta:
        model = StartupIdea
        fields = [
            "id",
            "username",
            "user_profile_picture",
            "name",
            "stage",
            "user_role",
            "user_role_display",
            "pitch",
            "description",
            "skills",
            "skills_list",
            "looking_for",
            "looking_for_list",
            "pitch_deck",
            "pitch_deck_url",
            "images",
            "website",
            "funding_stage",
            "investment_needed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "user_profile_picture",
            "user_role_display",
            "skills_list",
            "looking_for_list",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"pitch_deck": {"write_only": True}}

    def get_pitch_deck_url(self, obj):
        if obj.pitch_deck:
            return obj.pitch_deck.url
        return None

    def get_user_profile_picture(self, obj):
        if obj.user.profile_picture:
            return obj.user.profile_picture.url
        return None

    def get_looking_for_list(self, obj):
        return obj.looking_for_list

    def get_skills_list(self, obj):
        return obj.skills_list

    # Convert lists to comma-separated strings when saving
    def validate_looking_for(self, value):
        if isinstance(value, list):
            return ", ".join(value)
        return value

    def validate_skills(self, value):
        if isinstance(value, list):
            return ", ".join(value)
        return value
