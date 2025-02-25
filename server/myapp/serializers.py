from rest_framework import serializers
from .models import StartupProfile, StartupImage
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class StartupImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = StartupImage
        fields = ['id', 'image', 'image_url', 'caption', 'created_at']
        extra_kwargs = {
            'image': {'write_only': True}
        }

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None

class UserProfileImageSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'profile_picture', 'profile_picture_url']
        extra_kwargs = {
            'profile_picture': {'write_only': True}
        }

    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            return obj.profile_picture.url
        return None

class StartupProfileSerializer(serializers.ModelSerializer):
    images = StartupImageSerializer(many=True, read_only=True)
    pitch_deck_url = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    user_profile = UserProfileImageSerializer(source='user', read_only=True)

    class Meta:
        model = StartupProfile
        fields = [
            'id',
            'username',
            'email',
            'user_profile',
            'bio',
            'age',
            'location',
            'interests',
            'profile_images',
            'startup_name',
            'startup_stage',
            'pitch',
            'description',
            'role',
            'skills',
            'looking_for',
            'pitch_deck',
            'pitch_deck_url',
            'startup_images',
            'images',
            'website',
            'linkedin',
            'github',
            'funding_stage',
            'investment_needed',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'pitch_deck': {'write_only': True}
        }

    def get_pitch_deck_url(self, obj):
        if obj.pitch_deck:
            return obj.pitch_deck.url
        return None 