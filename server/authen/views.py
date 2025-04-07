from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.authentication import SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.http import Http404
from django.db.models import Q
from .serializers import (
    ContactLinkSerializer,
    TokenByUsernameSerializer,
    UserSerializer,
    UserInfoSerializer,
    LoginSerializer,
)
from .models import ContactLink, CustomUser
from .authentication import BearerTokenAuthentication
import logging
from rest_framework.views import APIView

from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .serializers import (
    ContactLinkSerializer,
    UserSerializer,
    UserInfoSerializer,
    LoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)

from django.core.mail import EmailMultiAlternatives
from datetime import datetime


class AuthViewSet(viewsets.ViewSet):
    """ViewSet for authentication-related actions"""

    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
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
                    "token_type": "Bearer",
                    "auth_header": f"Bearer {token.key}",
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
                "token_type": "Bearer",
                "auth_header": f"Bearer {token.key}",
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
        methods=["put"],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def update_profile(self, request):
        """Update user profile information using PUT method"""
        serializer = UserInfoSerializer(request.user, data=request.data)
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
                "token_type": "Bearer",
                "auth_header": f"Bearer {token.key}",
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
                    "token_type": "Bearer",
                    "auth_header": f"Bearer {token.key}",
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
                "token_type": "Bearer",
                "auth_header": f"Bearer {token.key}",
                "user": UserSerializer(user).data,
                "message": "Login successful",
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(generics.GenericAPIView):
    """Logout user by deleting token"""

    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
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

    serializer_class = UserSerializer
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "put", "delete", "post"]  # Add POST method
    lookup_field = "username"
    queryset = CustomUser.objects.all()

    def get_object(self):
        """
        Retrieve or create user profile
        """
        username = self.kwargs.get("username")
        if username:
            try:
                return CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                # If using POST and profile doesn't exist, create it for the current user
                if self.request.method == "POST":
                    return self.request.user
                raise Http404("User not found")
        return self.request.user

    def create(self, request, *args, **kwargs):
        """
        Create or update profile for the current user
        """
        # Ensure only authenticated users can create/update their own profile
        if request.user.username != kwargs.get("username", request.user.username):
            return Response(
                {"error": "You can only create/update your own profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Use the update method for creating/updating
        return self.update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve user profile"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        """Update user profile with full data using PUT"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Profile updated successfully", "user": serializer.data}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Delete user account"""
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

    def post(self, request, *args, **kwargs):
        """
        Handle profile creation or update
        """
        return self.create(request, *args, **kwargs)


class PasswordChangeView(generics.GenericAPIView):
    """Change user password with old password verification"""

    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
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
            {
                "message": "Password changed successfully",
                "token": token.key,
                "token_type": "Bearer",
                "auth_header": f"Bearer {token.key}",
            },
            status=status.HTTP_200_OK,
        )


class ProfileDetailView(generics.RetrieveAPIView):
    """View other user profiles by username"""

    serializer_class = UserInfoSerializer
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
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

    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TokenByUsernameSerializer

    def get(self, request, *args, **kwargs):
        """
        Get or create an auth token for the authenticated user
        """
        token, created = Token.objects.get_or_create(user=request.user)

        return Response(
            {
                "token": token.key,
                "token_type": "Bearer",
                "auth_header": f"Bearer {token.key}",
                "created": created,
                "user_id": request.user.id,
                "username": request.user.username,
            },
            status=status.HTTP_200_OK,
        )


class GetTokenByUsernameView(generics.GenericAPIView):
    """Retrieve or create a token for a user by username from URL path"""

    authentication_classes = []  # No authentication required for this endpoint
    permission_classes = [AllowAny]  # Allow anyone to request a token
    serializer_class = TokenByUsernameSerializer

    def get(self, request, username, *args, **kwargs):
        """
        Get a token for a user by username from URL path
        """
        try:
            # Get the user by username
            user = CustomUser.objects.get(username=username)

            # Get or create token
            token, created = Token.objects.get_or_create(user=user)

            return Response(
                {
                    "token": token.key,
                    "token_type": "Bearer",
                    "auth_header": f"Bearer {token.key}",
                    "user_id": user.id,
                    "username": user.username,
                },
                status=status.HTTP_200_OK,
            )
        except CustomUser.DoesNotExist:
            return Response(
                {"error": f"User with username '{username}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class AuthDebugView(generics.GenericAPIView):
    """Debug view to help diagnose authentication issues with detailed logging"""

    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]  # Allow unauthenticated access for debugging

    def get(self, request, *args, **kwargs):
        """Return debug information about the request's authentication and log it"""
        debug_info = self._get_debug_info(request)

        # Log the debugging information
        logger.info(
            f"AUTH DEBUG [{request.META.get('REMOTE_ADDR', 'unknown')}]: {debug_info}"
        )

        return Response(debug_info)

    def _get_debug_info(self, request):
        """Collect debugging information about the request's authentication"""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "None")
        token_param = request.GET.get("token", "None")

        # List all headers for debugging
        all_headers = {k: v for k, v in request.META.items() if k.startswith("HTTP_")}

        # Check if there's a token in the authorization header
        token_from_header = None
        if auth_header != "None":
            parts = auth_header.split()
            if len(parts) >= 2 and parts[0] in ["Bearer", "Token"]:
                token_from_header = parts[1]
            elif len(parts) == 1:
                token_from_header = parts[0]

        # Check if the token is valid
        token_valid = False
        user_from_token = None
        if token_from_header:
            try:
                token = Token.objects.get(key=token_from_header)
                token_valid = True
                user_from_token = {
                    "username": token.user.username,
                    "id": token.user.id,
                    "email": token.user.email,
                    "is_active": token.user.is_active,
                }
            except Token.DoesNotExist:
                pass
        elif token_param != "None":
            try:
                token = Token.objects.get(key=token_param)
                token_valid = True
                user_from_token = {
                    "username": token.user.username,
                    "id": token.user.id,
                    "email": token.user.email,
                    "is_active": token.user.is_active,
                }
            except Token.DoesNotExist:
                pass

        # Is the user authenticated in this request?
        is_authenticated = request.user.is_authenticated

        # Check if using session authentication
        using_session = False
        if is_authenticated and not token_valid:
            using_session = True

        return {
            "is_authenticated": is_authenticated,
            "user": request.user.username if is_authenticated else None,
            "auth_header": auth_header,
            "token_from_query_param": token_param,
            "token_from_header": token_from_header,
            "token_valid": token_valid,
            "user_from_token": user_from_token,
            "using_session": using_session,
            "method": request.method,
            "path": request.path,
            "auth_classes": [
                str(auth_class.__class__.__name__)
                for auth_class in self.authentication_classes
            ],
            "request_headers": all_headers,
        }


logger = logging.getLogger("django")


@api_view(["GET"])
@permission_classes([AllowAny])
def token_debug(request):
    """
    Special debugging endpoint to diagnose token issues.
    This endpoint doesn't require authentication and shows detailed
    information about the request headers.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "None")

    # Log the request for server-side debugging
    client_ip = get_client_ip(request)
    logger.info(f"TOKEN DEBUG REQUEST [{client_ip}]: {request.method} {request.path}")
    logger.info(f"TOKEN DEBUG AUTH HEADER: {auth_header}")

    # If there's an auth header, log detailed info about its format
    if auth_header != "None":
        logger.info(f"TOKEN DEBUG AUTH HEADER LENGTH: {len(auth_header)}")
        logger.info(f"TOKEN DEBUG AUTH HEADER PARTS: {auth_header.split()}")

        # Check for common formatting issues
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Skip "Bearer "
            logger.info(f"TOKEN DEBUG: Bearer prefix found, token length: {len(token)}")
        elif auth_header.startswith("Token "):
            token = auth_header[6:]  # Skip "Token "
            logger.info(f"TOKEN DEBUG: Token prefix found, token length: {len(token)}")
        elif " " not in auth_header:
            logger.info(
                f"TOKEN DEBUG: No prefix found, treating entire header as token"
            )

    # Build the response with detailed diagnostic information
    response_data = {
        "auth_header": auth_header,
        "auth_header_type": type(auth_header).__name__,
        "auth_header_length": len(auth_header) if auth_header != "None" else 0,
        "auth_parts": auth_header.split() if auth_header != "None" else [],
        "raw_headers": {k: v for k, v in request.META.items() if k.startswith("HTTP_")},
        "is_authenticated": request.user.is_authenticated,
        "user": str(request.user) if request.user.is_authenticated else "AnonymousUser",
        "message": "Use this information to debug token transmission issues",
    }

    return Response(response_data)


def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class CareerSummaryView(generics.RetrieveUpdateAPIView):
    """
    View to retrieve and update user's career summary
    """

    serializer_class = UserSerializer
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the current user
        """
        return self.request.user

    def update(self, request, *args, **kwargs):
        """
        Update only the career summary
        """
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data={"career_summary": request.data.get("career_summary")},
            partial=True,
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Career summary updated successfully",
                    "career_summary": serializer.data.get("career_summary"),
                }
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserSearchView(generics.ListAPIView):
    """
    View to search users based on various criteria
    """

    serializer_class = UserInfoSerializer
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # Fields to search across
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "email",
        "skills",
        "industry",
        "career_summary",
    ]

    # Fields to order by
    ordering_fields = ["username", "first_name", "last_name", "date_joined"]

    def get_queryset(self):
        """
        Retrieve and filter users
        Support multiple search and filter parameters
        """
        queryset = CustomUser.objects.all()

        # Filter by industry if provided
        industry = self.request.query_params.get("industry", None)
        if industry:
            queryset = queryset.filter(industry__icontains=industry)

        # Filter by skills
        skills = self.request.query_params.get("skills", None)
        if skills:
            # Split skills and filter users who have all skills
            skill_list = [skill.strip() for skill in skills.split(",")]
            for skill in skill_list:
                queryset = queryset.filter(skills__icontains=skill)

        # Filter by experience range
        min_experience = self.request.query_params.get("min_experience", None)
        max_experience = self.request.query_params.get("max_experience", None)
        if min_experience or max_experience:
            # Basic experience filtering (assumes experience is a string)
            if min_experience:
                queryset = queryset.filter(Q(experience__gte=min_experience))
            if max_experience:
                queryset = queryset.filter(Q(experience__lte=max_experience))

        return queryset


class PublicProfileView(generics.RetrieveAPIView):
    """
    View to retrieve public profile information
    Provides a limited view of user profile accessible without authentication
    """

    serializer_class = UserInfoSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "username"
    queryset = CustomUser.objects.all()

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve public profile with limited information
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            # Customize the response to return only public information
            public_data = {
                "id": serializer.data.get("id"),
                "username": serializer.data.get("username"),
                "first_name": serializer.data.get("first_name"),
                "last_name": serializer.data.get("last_name"),
                "profile_picture_url": serializer.data.get("profile_picture_url"),
                "bio": serializer.data.get("bio"),
                "industry": serializer.data.get("industry"),
                "skills": serializer.data.get("skills"),
                "past_projects": serializer.data.get("past_projects", ""),
                "career_summary": serializer.data.get("career_summary"),
            }

            return Response(public_data)
        except Http404:
            return Response(
                {"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ContactLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contact links
    Provides CRUD operations for contact links

    Endpoints:
    - GET /contact-links/ - List current user's contact links
    - POST /contact-links/ - Create a new contact link
    - GET /contact-links/{id}/ - Get a specific contact link
    - PUT/PATCH /contact-links/{id}/ - Update a contact link
    - DELETE /contact-links/{id}/ - Delete a contact link
    - GET /contact-links/my_links/ - Get current user's links (alias)
    - GET /contact-links/user/?username=X - Get links for username X
    - GET /contact-links/username/{username}/ - Get links for username (path-based)
    """

    serializer_class = ContactLinkSerializer
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]

    def get_permissions(self):
        """
        Dynamic permissions:
        - Public access for retrieving links by username
        - Authentication required for all other operations
        """
        if self.action == "retrieve_by_username":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """
        Return contact links based on parameters:
        - If username is provided in query params, return links for that user
        - Otherwise return current user's links
        """
        username = self.request.query_params.get("username", None)
        if username:
            try:
                user = CustomUser.objects.get(username=username)
                return ContactLink.objects.filter(user=user)
            except CustomUser.DoesNotExist:
                return ContactLink.objects.none()
        return ContactLink.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        Automatically associate the contact link with the current user
        """
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["GET"])
    def my_links(self, request):
        """
        Get all contact links for the current user
        """
        links = ContactLink.objects.filter(user=request.user)
        serializer = self.get_serializer(links, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def user(self, request):
        """
        Get all contact links for a specified user by username
        """
        username = request.query_params.get("username")
        if not username:
            return Response(
                {"error": "Username parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(username=username)
            links = ContactLink.objects.filter(user=user)
            serializer = self.get_serializer(links, many=True)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        """
        Custom destroy method to ensure user can only delete their own links
        """
        instance = self.get_object()
        if instance.user != request.user:
            return Response(
                {"error": "You do not have permission to delete this contact link."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["get"],
        url_path="username/(?P<username>[^/.]+)",
        permission_classes=[AllowAny],
    )
    def retrieve_by_username(self, request, username=None):
        """
        Get contact links for a specific username.
        This explicitly handles the URL path with username parameter.
        This endpoint is public and doesn't require authentication.
        """
        try:
            user = CustomUser.objects.get(username=username)
            links = ContactLink.objects.filter(user=user)
            serializer = self.get_serializer(links, many=True)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": f"User '{username}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class PublicContactLinksView(generics.ListAPIView):
    """
    View to retrieve public contact links for a specific user
    """

    serializer_class = ContactLinkSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Retrieve contact links for a specific username
        """
        username = self.kwargs.get("username")
        try:
            user = CustomUser.objects.get(username=username)
            return ContactLink.objects.filter(user=user)
        except CustomUser.DoesNotExist:
            return ContactLink.objects.none()


class UserContactLinksView(generics.ListAPIView):
    """
    View to retrieve contact links for a specific user by username
    This endpoint requires authentication but allows viewing any user's links
    """

    serializer_class = ContactLinkSerializer
    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Retrieve contact links for a specific username
        """
        username = self.kwargs.get("username")
        try:
            user = CustomUser.objects.get(username=username)
            return ContactLink.objects.filter(user=user)
        except CustomUser.DoesNotExist:
            return ContactLink.objects.none()


class UserContactLinksAPIView(APIView):
    """
    Simple API view to get contact links by username
    """

    authentication_classes = [BearerTokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, username, format=None):
        try:
            user = CustomUser.objects.get(username=username)
            links = ContactLink.objects.filter(user=user)
            serializer = ContactLinkSerializer(links, many=True)
            return Response(serializer.data)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": f"User '{username}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class PasswordResetRequestView(generics.GenericAPIView):
    """View for requesting a password reset via email"""

    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    # In views.py, modify the PasswordResetRequestView

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = CustomUser.objects.get(email=email)

                # Generate token and encoded uid
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                # Build reset URL
                reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

                # Create improved HTML email content
                email_body = f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            max-width: 600px;
                            margin: 0 auto;
                            padding: 20px;
                            background-color: #f4f4f4;
                        }}
                        .container {{
                            background-color: white;
                            border-radius: 8px;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            padding: 20px;
                        }}
                        .header {{
                            background-color: #007bff;
                            color: white;
                            text-align: center;
                            padding: 10px;
                            border-radius: 4px;
                            margin-bottom: 20px;
                        }}
                        .content {{
                            padding: 15px;
                        }}
                        .reset-link {{
                            display: block;
                            background-color: #007bff;
                            color: white;
                            text-align: center;
                            padding: 10px;
                            text-decoration: none;
                            border-radius: 4px;
                            margin: 20px 0;
                        }}
                        .footer {{
                            text-align: center;
                            color: #666;
                            font-size: 12px;
                            margin-top: 20px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>Password Reset</h2>
                        </div>
                        <div class="content">
                            <p>Hi {user.username},</p>
                            <p>You have requested to reset your password for Startup Hub. Click the button below to reset your password:</p>
                            
                            <a href="{reset_url}" class="reset-link">Reset Password</a>
                            
                            <p>If you did not request this password reset, please ignore this email or contact support if you have concerns.</p>
                            
                            <p>This password reset link will expire in 1 hour.</p>
                        </div>
                        <div class="footer">
                            <p>© {datetime.now().year} Startup Hub. All rights reserved.</p>
                            <p>If the button doesn't work, copy and paste this link:</p>
                            <p>{reset_url}</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Send email using EmailMultiAlternatives for HTML support
                from django.core.mail import EmailMultiAlternatives
                from datetime import datetime

                email = EmailMultiAlternatives(
                    subject="Reset Your Startup Hub Password",
                    body="Plain text fallback for email clients that don't support HTML",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email.attach_alternative(email_body, "text/html")
                email.send()

                return Response(
                    {"message": "Password reset email has been sent."},
                    status=status.HTTP_200_OK,
                )
            except CustomUser.DoesNotExist:
                # Don't reveal that the user doesn't exist for security reasons
                return Response(
                    {
                        "message": "Password reset email has been sent if the account exists."
                    },
                    status=status.HTTP_200_OK,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(generics.GenericAPIView):
    """View for confirming a password reset with a token"""

    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            uid = serializer.validated_data["uid"]
            token = serializer.validated_data["token"]
            new_password = serializer.validated_data["new_password"]

            try:
                # Decode the user ID
                user_id = force_str(urlsafe_base64_decode(uid))
                user = CustomUser.objects.get(pk=user_id)

                # Check if token is valid
                if default_token_generator.check_token(user, token):
                    # Set new password
                    user.set_password(new_password)
                    user.save()

                    # Invalidate existing auth tokens for security
                    if hasattr(user, "auth_token"):
                        user.auth_token.delete()

                    # Create a new token
                    token, _ = Token.objects.get_or_create(user=user)

                    return Response(
                        {
                            "message": "Password has been reset successfully.",
                            "token": token.key,
                            "token_type": "Bearer",
                            "auth_header": f"Bearer {token.key}",
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Invalid or expired token"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
                return Response(
                    {"error": "Invalid reset link"}, status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
