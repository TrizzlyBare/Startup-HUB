from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Participant
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone
from message.models import (
    Room as MessageRoom,
    Participant as MessageParticipant,
    Message,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_room(request):
    """Create a new video call room"""
    name = request.data.get("name")
    max_participants = request.data.get("max_participants", 10)
    is_recording_enabled = request.data.get("is_recording_enabled", False)
    message_room_id = request.data.get("message_room_id")

    # Validate message room ID if provided
    if message_room_id:
        try:
            message_room = MessageRoom.objects.get(id=message_room_id)

            # Check if user is a participant in the message room
            if not MessageParticipant.objects.filter(
                user=request.user, room=message_room
            ).exists():
                return Response(
                    {
                        "success": False,
                        "error": "You are not a participant in the specified message room",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Use message room name if name not provided
            if not name:
                name = f"Call in {message_room.name}"

        except MessageRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Message room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    room = Room.objects.create(
        name=name,
        max_participants=max_participants,
        is_recording_enabled=is_recording_enabled,
    )

    # Add the creator as the first participant
    participant = Participant.objects.create(
        user=request.user, room=room, last_active=timezone.now()
    )

    # If message room ID is provided, store it in room metadata
    if message_room_id:
        # Create a message in the chat room about the video call
        try:
            message = Message.objects.create(
                room_id=message_room_id,
                sender=request.user,
                content=f"Started a video call",
            )

            # Notify users in the message room about the video call
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{message_room_id}",
                {
                    "type": "notification",
                    "message": "video_call_started",
                    "data": {
                        "video_room_id": str(room.id),
                        "message_room_id": message_room_id,
                        "initiator_id": request.user.id,
                        "initiator_username": request.user.username,
                    },
                },
            )
        except Exception as e:
            # Don't fail if notification fails
            print(f"Error notifying about video call: {e}")

    return Response(
        {
            "success": True,
            "room": {
                "id": str(room.id),
                "name": room.name,
                "created_at": room.created_at,
                "max_participants": room.max_participants,
                "is_recording_enabled": room.is_recording_enabled,
                "is_active": room.is_active,
            },
            "message_room_id": message_room_id,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_room(request, room_id):
    """Join an existing video call room"""
    room = get_object_or_404(Room, id=room_id)
    message_room_id = request.data.get("message_room_id")

    # Check if the room is active
    if not room.is_active:
        return Response(
            {"success": False, "error": "This room is no longer active"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if room is at capacity
    current_participants = Participant.objects.filter(room=room).count()
    if current_participants >= room.max_participants:
        return Response(
            {"success": False, "error": "Room is at maximum capacity"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # If message room ID is provided, verify the user is a participant
    if message_room_id:
        try:
            message_room = MessageRoom.objects.get(id=message_room_id)
            if not MessageParticipant.objects.filter(
                user=request.user, room=message_room
            ).exists():
                return Response(
                    {
                        "success": False,
                        "error": "You are not a participant in the specified message room",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
        except MessageRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Message room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Join the room
    participant, created = Participant.objects.get_or_create(
        user=request.user, room=room, defaults={"last_active": timezone.now()}
    )

    # If not created, update the last_active time
    if not created:
        participant.last_active = timezone.now()
        participant.save(update_fields=["last_active"])

    # Notify other participants through WebSockets (if they're connected)
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"call_{room.id}",
            {
                "type": "user_joined",
                "user_id": request.user.id,
                "username": request.user.username,
            },
        )

        # Also notify the message room if specified
        if message_room_id:
            async_to_sync(channel_layer.group_send)(
                f"chat_{message_room_id}",
                {
                    "type": "notification",
                    "message": "video_call_joined",
                    "data": {
                        "video_room_id": str(room.id),
                        "message_room_id": message_room_id,
                        "user_id": request.user.id,
                        "username": request.user.username,
                    },
                },
            )

            # Create a system message in the chat
            Message.objects.create(
                room_id=message_room_id,
                sender=request.user,
                content=f"joined the video call",
            )
    except Exception as e:
        # Don't fail if the WebSocket notification fails
        print(f"Error in WebSocket notification: {e}")

    return Response(
        {
            "success": True,
            "room": {
                "id": str(room.id),
                "name": room.name,
                "created_at": room.created_at,
                "max_participants": room.max_participants,
                "is_recording_enabled": room.is_recording_enabled,
                "is_active": room.is_active,
            },
            "message_room_id": message_room_id,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_room_participants(request, room_id):
    """Get participants in a video call room"""
    room = get_object_or_404(Room, id=room_id)
    message_room_id = request.query_params.get("message_room_id")

    # Check if user is a participant
    if not Participant.objects.filter(user=request.user, room=room).exists():
        return Response(
            {"success": False, "error": "You are not a participant in this room"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get participants who were active in the last minute
    one_minute_ago = timezone.now() - timezone.timedelta(minutes=1)
    active_participants = Participant.objects.filter(
        room=room, last_active__gte=one_minute_ago
    ).select_related("user")

    # If message room ID is provided, filter to only include participants from that room
    if message_room_id:
        try:
            # Verify message room exists
            message_room = MessageRoom.objects.get(id=message_room_id)

            # Get all users in the message room
            message_participants = set(
                MessageParticipant.objects.filter(room=message_room).values_list(
                    "user_id", flat=True
                )
            )

            # Filter active participants to only those in the message room
            active_participants = [
                p for p in active_participants if p.user_id in message_participants
            ]

        except MessageRoom.DoesNotExist:
            return Response(
                {"success": False, "error": "Message room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    return Response(
        {
            "success": True,
            "active_participants": [
                {
                    "id": p.id,
                    "user_id": p.user.id,
                    "username": p.user.username,
                    "joined_at": p.joined_at,
                    "is_audio_muted": p.is_audio_muted,
                    "is_video_muted": p.is_video_muted,
                }
                for p in active_participants
            ],
            "room": {
                "id": str(room.id),
                "name": room.name,
                "created_at": room.created_at,
                "max_participants": room.max_participants,
                "is_recording_enabled": room.is_recording_enabled,
            },
            "message_room_id": message_room_id,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave_room(request, room_id):
    """Leave a video call room"""
    room = get_object_or_404(Room, id=room_id)
    message_room_id = request.data.get("message_room_id")

    # Remove the participant
    participant = get_object_or_404(Participant, user=request.user, room=room)
    participant.delete()

    # Notify other participants through WebSockets
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"call_{room.id}",
            {
                "type": "user_left",
                "user_id": request.user.id,
                "username": request.user.username,
            },
        )

        # Also notify the message room if specified
        if message_room_id:
            async_to_sync(channel_layer.group_send)(
                f"chat_{message_room_id}",
                {
                    "type": "notification",
                    "message": "video_call_left",
                    "data": {
                        "video_room_id": str(room.id),
                        "message_room_id": message_room_id,
                        "user_id": request.user.id,
                        "username": request.user.username,
                    },
                },
            )

            # Create a system message in the chat
            Message.objects.create(
                room_id=message_room_id,
                sender=request.user,
                content=f"left the video call",
            )
    except Exception as e:
        # Don't fail if the WebSocket notification fails
        print(f"Error in WebSocket notification: {e}")

    return Response({"success": True, "message": "You have left the room"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_media_status(request, room_id):
    """Update audio/video mute status"""
    room = get_object_or_404(Room, id=room_id)
    participant = get_object_or_404(Participant, user=request.user, room=room)

    # Update participant status
    if "is_audio_muted" in request.data:
        participant.is_audio_muted = request.data["is_audio_muted"]

    if "is_video_muted" in request.data:
        participant.is_video_muted = request.data["is_video_muted"]

    participant.last_active = timezone.now()
    participant.save()

    # Notify other participants through WebSockets
    channel_layer = get_channel_layer()

    if "is_audio_muted" in request.data:
        try:
            async_to_sync(channel_layer.group_send)(
                f"call_{room.id}",
                {
                    "type": "audio_status",
                    "user_id": request.user.id,
                    "username": request.user.username,
                    "muted": participant.is_audio_muted,
                },
            )
        except Exception:
            pass

    if "is_video_muted" in request.data:
        try:
            async_to_sync(channel_layer.group_send)(
                f"call_{room.id}",
                {
                    "type": "video_status",
                    "user_id": request.user.id,
                    "username": request.user.username,
                    "muted": participant.is_video_muted,
                },
            )
        except Exception:
            pass

    return Response(
        {
            "success": True,
            "is_audio_muted": participant.is_audio_muted,
            "is_video_muted": participant.is_video_muted,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_to_call(request, room_id):
    """Invite a user from the message room to join the video call"""
    video_room = get_object_or_404(Room, id=room_id)
    message_room_id = request.data.get("message_room_id")
    user_id = request.data.get("user_id")

    if not message_room_id or not user_id:
        return Response(
            {"success": False, "error": "message_room_id and user_id are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Verify message room exists
        message_room = MessageRoom.objects.get(id=message_room_id)

        # Check if the current user is a participant in both rooms
        if not MessageParticipant.objects.filter(
            user=request.user, room=message_room
        ).exists():
            return Response(
                {
                    "success": False,
                    "error": "You are not a participant in the specified message room",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not Participant.objects.filter(user=request.user, room=video_room).exists():
            return Response(
                {
                    "success": False,
                    "error": "You are not a participant in the specified video call room",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if the invited user is a participant in the message room
        invited_user_participant = (
            MessageParticipant.objects.filter(user_id=user_id, room=message_room)
            .select_related("user")
            .first()
        )

        if not invited_user_participant:
            return Response(
                {
                    "success": False,
                    "error": "The invited user is not a participant in the message room",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Send invitation notification via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",  # Send to specific user
            {
                "type": "notification",
                "message": "video_call_invitation",
                "data": {
                    "video_room_id": str(video_room.id),
                    "message_room_id": message_room_id,
                    "inviter_id": request.user.id,
                    "inviter_username": request.user.username,
                    "room_name": video_room.name,
                },
            },
        )

        # Also send a notification to the message room
        async_to_sync(channel_layer.group_send)(
            f"chat_{message_room_id}",
            {
                "type": "notification",
                "message": "video_call_invitation_sent",
                "data": {
                    "video_room_id": str(video_room.id),
                    "message_room_id": message_room_id,
                    "inviter_id": request.user.id,
                    "inviter_username": request.user.username,
                    "invited_user_id": user_id,
                    "invited_username": invited_user_participant.user.username,
                },
            },
        )

        # Create a system message in the chat
        Message.objects.create(
            room=message_room,
            sender=request.user,
            content=f"invited {invited_user_participant.user.username} to join a video call",
        )

        return Response(
            {
                "success": True,
                "message": f"Invitation sent to {invited_user_participant.user.username}",
            }
        )

    except MessageRoom.DoesNotExist:
        return Response(
            {"success": False, "error": "Message room not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def respond_to_invitation(request):
    """Respond to a video call invitation"""
    video_room_id = request.data.get("video_room_id")
    message_room_id = request.data.get("message_room_id")
    response_type = request.data.get("response")  # 'accept' or 'decline'

    if not video_room_id or not message_room_id or not response_type:
        return Response(
            {
                "success": False,
                "error": "video_room_id, message_room_id, and response are required",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if response_type not in ["accept", "decline"]:
        return Response(
            {
                "success": False,
                "error": "Response must be either 'accept' or 'decline'",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        video_room = Room.objects.get(id=video_room_id)
        message_room = MessageRoom.objects.get(id=message_room_id)

        # Check if user is part of the message room
        if not MessageParticipant.objects.filter(
            user=request.user, room=message_room
        ).exists():
            return Response(
                {
                    "success": False,
                    "error": "You are not a participant in the specified message room",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Send response notification via WebSocket
        channel_layer = get_channel_layer()
        if response_type == "accept":
            # Notify video room about the accepted invitation
            async_to_sync(channel_layer.group_send)(
                f"call_{video_room_id}",
                {
                    "type": "notification",
                    "message": "video_call_accepted",
                    "data": {
                        "user_id": request.user.id,
                        "username": request.user.username,
                        "video_room_id": video_room_id,
                        "message_room_id": message_room_id,
                    },
                },
            )

            # Notify message room about the accepted invitation
            async_to_sync(channel_layer.group_send)(
                f"chat_{message_room_id}",
                {
                    "type": "notification",
                    "message": "video_call_accepted",
                    "data": {
                        "user_id": request.user.id,
                        "username": request.user.username,
                        "video_room_id": video_room_id,
                        "message_room_id": message_room_id,
                    },
                },
            )

            # Create a system message in the chat
            Message.objects.create(
                room=message_room, sender=request.user, content=f"joined the video call"
            )

            # Join the video room
            participant, created = Participant.objects.get_or_create(
                user=request.user,
                room=video_room,
                defaults={"last_active": timezone.now()},
            )

            # If not created, update the last_active time
            if not created:
                participant.last_active = timezone.now()
                participant.save(update_fields=["last_active"])

            return Response(
                {
                    "success": True,
                    "message": "Invitation accepted",
                    "room": {
                        "id": str(video_room.id),
                        "name": video_room.name,
                        "created_at": video_room.created_at,
                        "max_participants": video_room.max_participants,
                        "is_recording_enabled": video_room.is_recording_enabled,
                        "is_active": video_room.is_active,
                    },
                }
            )

        else:  # decline
            # Notify video room about the declined invitation
            async_to_sync(channel_layer.group_send)(
                f"call_{video_room_id}",
                {
                    "type": "notification",
                    "message": "video_call_declined",
                    "data": {
                        "user_id": request.user.id,
                        "username": request.user.username,
                        "video_room_id": video_room_id,
                        "message_room_id": message_room_id,
                    },
                },
            )

            # Create a system message in the chat
            Message.objects.create(
                room=message_room,
                sender=request.user,
                content=f"declined to join the video call",
            )

            return Response({"success": True, "message": "Invitation declined"})

    except Room.DoesNotExist:
        return Response(
            {"success": False, "error": "Video room not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except MessageRoom.DoesNotExist:
        return Response(
            {"success": False, "error": "Message room not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def active_calls(request):
    """Get list of active video calls related to message rooms the user is part of"""

    # Get all message rooms the user is part of
    message_rooms = MessageRoom.objects.filter(
        participants__user=request.user
    ).values_list("id", flat=True)

    # Find rooms where the user is a participant and the room is active
    rooms = Room.objects.filter(
        participants__user=request.user, is_active=True
    ).distinct()

    # Get all active participants
    one_minute_ago = timezone.now() - timezone.timedelta(minutes=1)

    room_data = []
    for room in rooms:
        active_participants = Participant.objects.filter(
            room=room, last_active__gte=one_minute_ago
        ).select_related("user")

        # Check if any of the active participants are also in message rooms the user is part of
        common_participants = []
        for participant in active_participants:
            common_message_rooms = MessageParticipant.objects.filter(
                user=participant.user, room_id__in=message_rooms
            ).values_list("room_id", flat=True)

            if common_message_rooms:
                common_participants.append(
                    {
                        "user_id": participant.user.id,
                        "username": participant.user.username,
                        "common_message_rooms": list(map(str, common_message_rooms)),
                    }
                )

        if common_participants:
            room_data.append(
                {
                    "id": str(room.id),
                    "name": room.name,
                    "created_at": room.created_at,
                    "active_participants_count": len(active_participants),
                    "common_participants": common_participants,
                }
            )

    return Response({"success": True, "rooms": room_data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_call(request, room_id):
    """End a video call and notify all participants"""
    room = get_object_or_404(Room, id=room_id)
    message_room_id = request.data.get("message_room_id")

    # Check if user is a participant in the room
    if not Participant.objects.filter(user=request.user, room=room).exists():
        return Response(
            {"success": False, "error": "You are not a participant in this room"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Mark the room as inactive
    room.is_active = False
    room.save()

    # Notify all participants
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            f"call_{room.id}",
            {
                "type": "notification",
                "message": "video_call_ended",
                "data": {
                    "video_room_id": str(room.id),
                    "message_room_id": message_room_id,
                    "ended_by_id": request.user.id,
                    "ended_by_username": request.user.username,
                },
            },
        )

        # Also notify the message room if specified
        if message_room_id:
            try:
                message_room = MessageRoom.objects.get(id=message_room_id)

                # Create a system message in the chat
                Message.objects.create(
                    room=message_room,
                    sender=request.user,
                    content=f"ended the video call",
                )

                async_to_sync(channel_layer.group_send)(
                    f"chat_{message_room_id}",
                    {
                        "type": "notification",
                        "message": "video_call_ended",
                        "data": {
                            "video_room_id": str(room.id),
                            "message_room_id": message_room_id,
                            "ended_by_id": request.user.id,
                            "ended_by_username": request.user.username,
                        },
                    },
                )
            except MessageRoom.DoesNotExist:
                pass
    except Exception as e:
        # Don't fail if notification fails
        print(f"Error notifying about call end: {e}")

    return Response({"success": True, "message": "Call ended successfully"})
