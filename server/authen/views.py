from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.http import Http404
from .serializers import UserSerializer, UserInfoSerializer, LoginSerializer
from .models import CustomUser


class AuthViewSet(viewsets.ViewSet):
    """ViewSet for authentication-related actions"""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ["register", "login"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer(self, *args, **kwargs):
        """
        This method is needed for the browsable API to render forms
        """
        serializer_class = UserSerializer
        kwargs.setdefault("context", {"request": self.request})
        return serializer_class(*args, **kwargs)

    @action(detail=False, methods=["post"])
    def register(self, request):
        """Handle user registration with profile picture upload"""
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            if CustomUser.objects.filter(
                email=serializer.validated_data["email"]
            ).exists():
                return Response(
                    {"error": "Email already in use"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Save the user
            user = serializer.save()

            # Generate a token for the user
            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "token": token.key,
                    "user": UserSerializer(user).data,
                    "message": "User registered successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def login(self, request):
        """Handle user login and return authentication token"""
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            # First try to get the user by email
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Use Django's authenticate method with username and password
        user = authenticate(username=user.username, password=password)
        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Always create a new token to ensure it's valid
        if hasattr(user, "auth_token"):
            user.auth_token.delete()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    def logout(self, request):
        """Handle user logout by deleting the token"""
        try:
            # Delete the user's token to logout
            if hasattr(request.user, "auth_token"):
                request.user.auth_token.delete()
            return Response(
                {"message": "Successfully logged out"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Logout failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["patch"],  # Changed from 'put' to 'patch'
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def update_profile(self, request):
        """Update user profile information using PATCH method"""
        serializer = UserInfoSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Profile updated successfully", "user": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["delete"])
    def delete_account(self, request):
        """Delete user account"""
        user = request.user

        # Delete auth token first
        if hasattr(user, "auth_token"):
            user.auth_token.delete()

        # Delete the user account
        user.delete()

        return Response(
            {"message": "Your account has been permanently deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["get"])
    def token(self, request):
        """Get or create the user's authentication token"""
        token, created = Token.objects.get_or_create(user=request.user)

        return Response(
            {
                "token": token.key,
                "created": created,
                "user_id": request.user.id,
                "username": request.user.username,
            },
            status=status.HTTP_200_OK,
        )


# Additional standalone generic views for better browser interaction
class RegisterView(generics.CreateAPIView):
    """Register a new user and return token"""

    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            if CustomUser.objects.filter(
                email=serializer.validated_data["email"]
            ).exists():
                return Response(
                    {"error": "Email already in use"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "token": token.key,
                    "user": UserSerializer(user).data,
                    "message": "User registered successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(generics.GenericAPIView):
    """Login user and return token"""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    http_method_names = ["post", "get"]  # Allow both POST and GET for form rendering

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(username=user.username, password=password)
        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Always create a new token to ensure it's valid
        if hasattr(user, "auth_token"):
            user.auth_token.delete()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": UserSerializer(user).data,
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(generics.GenericAPIView):
    """Logout user by deleting token"""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            if hasattr(request.user, "auth_token"):
                request.user.auth_token.delete()
            return Response(
                {"message": "Successfully logged out"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"Logout failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ProfileView(generics.RetrieveUpdateDestroyAPIView):
    """View, update and delete user profile"""

    serializer_class = UserInfoSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "patch", "delete"]  # Changed 'put' to 'patch'

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        """Update user profile with partial data using PATCH"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Profile updated successfully", "user": serializer.data}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        # Delete auth token first if it exists
        if hasattr(user, "auth_token"):
            user.auth_token.delete()

        # Delete the user account
        user.delete()

        return Response(
            {"message": "Your account has been permanently deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )


class PasswordChangeView(generics.GenericAPIView):
    """Change user password with old password verification"""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"error": "Both old and new passwords are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not user.check_password(old_password):
            return Response(
                {"error": "Old password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        # Update token to force re-login with new password
        if hasattr(user, "auth_token"):
            user.auth_token.delete()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {"message": "Password changed successfully", "token": token.key},
            status=status.HTTP_200_OK,
        )


class ProfileDetailView(generics.RetrieveAPIView):
    """View other user profiles by username"""

    serializer_class = UserInfoSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = CustomUser.objects.all()
    lookup_field = "username"

    def get_object(self):
        username = self.kwargs.get("username")

        if username:
            try:
                return CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                raise Http404("User not found")

        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class GetTokenView(generics.GenericAPIView):
    """Retrieve current user's token"""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Get or create an auth token for the authenticated user
        """
        token, created = Token.objects.get_or_create(user=request.user)

        return Response(
            {
                "token": token.key,
                "created": created,
                "user_id": request.user.id,
                "username": request.user.username,
            },
            status=status.HTTP_200_OK,
        )
