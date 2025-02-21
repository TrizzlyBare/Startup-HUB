from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from .models import StartupProfile, StartupImage
from .serializers import StartupProfileSerializer, StartupImageSerializer, UserProfileImageSerializer
from django.db.models import Q
import cloudinary


# Create your views here.
def home(request):
    return HttpResponse("Hello, Django!")

class StartupProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StartupProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return StartupProfile.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def upload_image(self, request, pk=None):
        profile = self.get_object()
        image = request.FILES.get('image')
        caption = request.data.get('caption', '')

        if not image:
            return Response(
                {'error': 'No image provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        startup_image = StartupImage.objects.create(
            profile=profile,
            image=image,
            caption=caption
        )

        return Response(
            StartupImageSerializer(startup_image).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def upload_pitch_deck(self, request, pk=None):
        profile = self.get_object()
        pitch_deck = request.FILES.get('pitch_deck')

        if not pitch_deck:
            return Response(
                {'error': 'No pitch deck provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.pitch_deck = pitch_deck
        profile.save()

        return Response(
            StartupProfileSerializer(profile).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        profile = get_object_or_404(StartupProfile, user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        role = request.query_params.get('role', '')
        skills = request.query_params.get('skills', '').split(',')
        stage = request.query_params.get('stage', '')

        queryset = self.get_queryset()

        if role:
            queryset = queryset.filter(role=role)
        if skills:
            queryset = queryset.filter(skills__contains=skills)
        if stage:
            queryset = queryset.filter(startup_stage=stage)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def upload_profile_images(self, request, pk=None):
        """Upload multiple profile images"""
        profile = self.get_object()
        images = request.FILES.getlist('images')

        if not images:
            return Response(
                {'error': 'No images provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get existing profile images
        current_images = profile.profile_images or []

        # Upload new images to Cloudinary and store URLs
        for image in images:
            cloudinary_response = cloudinary.uploader.upload(
                image,
                folder='startup_hub/profile_images',
                transformation={
                    'width': 500,
                    'height': 500,
                    'crop': 'fill',
                    'gravity': 'face'
                }
            )
            current_images.append(cloudinary_response['secure_url'])

        # Update profile with new images
        profile.profile_images = current_images
        profile.save()

        return Response(
            StartupProfileSerializer(profile).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def update_main_profile_picture(self, request, pk=None):
        """Update the main profile picture in CustomUser model"""
        profile = self.get_object()
        image = request.FILES.get('image')

        if not image:
            return Response(
                {'error': 'No image provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the user's profile picture
        profile.user.profile_picture = image
        profile.user.save()

        return Response(
            UserProfileImageSerializer(profile.user).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['delete'])
    def remove_profile_image(self, request, pk=None):
        """Remove a specific profile image"""
        profile = self.get_object()
        image_url = request.data.get('image_url')

        if not image_url:
            return Response(
                {'error': 'No image URL provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Remove image from profile_images list
        if image_url in profile.profile_images:
            profile.profile_images.remove(image_url)
            profile.save()

        return Response(
            StartupProfileSerializer(profile).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def match_suggestions(self, request):
        """Get potential matches based on roles and skills"""
        user_profile = get_object_or_404(StartupProfile, user=request.user)
        
        # Get profiles looking for user's role or having skills user is looking for
        matches = StartupProfile.objects.exclude(user=request.user).filter(
            Q(looking_for__contains=[user_profile.role]) |
            Q(skills__overlap=user_profile.looking_for)
        )

        serializer = self.get_serializer(matches, many=True)
        return Response(serializer.data)
