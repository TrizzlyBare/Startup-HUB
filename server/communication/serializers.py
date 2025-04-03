from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room, Message, Participant, CallLog
from rest_framework import serializers
from .models import MediaFile
from .utils import CloudinaryHelper


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class ParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Participant
        fields = ["user", "joined_at", "is_admin", "is_muted"]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "room",
            "sender",
            "content",
            "message_type",
            "image",
            "video",
            "audio",
            "document",
            "latitude",
            "longitude",
            "sent_at",
            "is_read",
            "call_duration",
            "call_type",
            "call_status",
        ]


class RoomSerializer(serializers.ModelSerializer):
    participants = ParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = [
            "id",
            "name",
            "room_type",
            "created_at",
            "updated_at",
            "is_active",
            "max_participants",
            "profile_image",
            "participants",
            "last_message",
        ]

    def get_last_message(self, obj):
        last_message = obj.messages.order_by("-sent_at").first()
        return MessageSerializer(last_message).data if last_message else None


class CallLogSerializer(serializers.ModelSerializer):
    caller = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = CallLog
        fields = "__all__"


class MediaFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = [
            "id",
            "name",
            "file",
            "media_type",
            "uploaded_at",
            "file_url",
            "public_id",
        ]
        read_only_fields = ["uploaded_at", "file_url", "public_id"]

    def get_file_url(self, obj):
        """
        Get transformed URL with optional parameters
        """
        width = self.context.get("width")
        height = self.context.get("height")

        if obj.public_id:
            return CloudinaryHelper.generate_transformation_url(
                obj.public_id, width=width, height=height
            )
        return None

    def create(self, validated_data):
        """
        Custom create method to handle Cloudinary upload
        """
        file = validated_data.pop("file")
        user = self.context["request"].user

        # Determine media type
        media_type = validated_data.get(
            "media_type", "image" if file.content_type.startswith("image") else "video"
        )

        # Upload to Cloudinary based on media type
        if media_type == "image":
            upload_result = CloudinaryHelper.upload_image(file)
        elif media_type == "video":
            upload_result = CloudinaryHelper.upload_video(file)
        else:
            upload_result = CloudinaryHelper.upload_image(file, resource_type="raw")

        if upload_result:
            validated_data["file"] = upload_result["url"]
            validated_data["public_id"] = upload_result["public_id"]
            validated_data["user"] = user

            return super().create(validated_data)

        raise serializers.ValidationError("Upload failed")


class CallInvitationSerializer(serializers.ModelSerializer):
    inviter = UserSerializer(read_only=True)
    invitee = UserSerializer(read_only=True)

    class Meta:
        model = CallInvitation
        fields = [
            "id",
            "inviter",
            "invitee",
            "room",
            "call_type",
            "created_at",
            "expires_at",
            "status",
        ]
