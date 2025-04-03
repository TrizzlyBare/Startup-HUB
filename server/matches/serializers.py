from rest_framework import serializers
from .models import Match, Like, Dislike
from authen.models import CustomUser
from authen.serializers import UserInfoSerializer


class MatchSerializer(serializers.ModelSerializer):
    matched_user_details = UserInfoSerializer(source="matched_user", read_only=True)
    user_details = UserInfoSerializer(source="user", read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "user",
            "matched_user",
            "matched_user_details",
            "user_details",
            "created_at",
            "is_mutual",
        ]
        read_only_fields = ["id", "user", "created_at", "is_mutual"]


class LikeSerializer(serializers.ModelSerializer):
    liked_user_details = UserInfoSerializer(source="liked_user", read_only=True)

    class Meta:
        model = Like
        fields = ["id", "user", "liked_user", "liked_user_details", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class DislikeSerializer(serializers.ModelSerializer):
    disliked_user_details = UserInfoSerializer(source="disliked_user", read_only=True)

    class Meta:
        model = Dislike
        fields = ["id", "user", "disliked_user", "disliked_user_details", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class PotentialMatchSerializer(serializers.ModelSerializer):
    """Serializer for listing potential matches (users to swipe on)"""

    profile_picture_url = serializers.SerializerMethodField()
    contact_links = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "profile_picture_url",
            "bio",
            "industry",
            "experience",
            "skills",
            "contact_links",
        ]

    def get_profile_picture_url(self, obj):
        """Get the Cloudinary URL for the profile picture"""
        if obj.profile_picture:
            return obj.profile_picture.url
        return None

    def get_contact_links(self, obj):
        from authen.serializers import ContactLinkSerializer

        return ContactLinkSerializer(obj.contact_links.all(), many=True).data
