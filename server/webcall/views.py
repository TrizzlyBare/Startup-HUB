from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Participant
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_room(request):
    """Create a new video call room"""
    name = request.data.get("name")
    max_participants = request.data.get("max_participants", 10)
    is_recording_enabled = request.data.get("is_recording_enabled", False)

    room = Room.objects.create(
        name=name,
        max_participants=max_participants,
        is_recording_enabled=is_recording_enabled,
    )

    # Add the creator as the first participant
    Participant.objects.create(user=request.user, room=room, last_active=timezone.now())

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
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_room(request, room_id):
    """Join an existing video call room"""
    room = get_object_or_404(Room, id=room_id)

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

    # Join the room
    participant, created = Participant.objects.get_or_create(
        user=request.user, room=room, defaults={"last_active": timezone.now()}
    )

    # If not created, update the last_active time
    if not created:
        participant.last_active = timezone.now()
        participant.save(update_fields=["last_active"])

    # Notify other participants through WebSockets
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
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_room_participants(request, room_id):
    """Get participants in a video call room"""
    room = get_object_or_404(Room, id=room_id)

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
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def leave_room(request, room_id):
    """Leave a video call room"""
    room = get_object_or_404(Room, id=room_id)

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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def active_calls(request):
    """Get list of active video calls"""
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

        room_data.append(
            {
                "id": str(room.id),
                "name": room.name,
                "created_at": room.created_at,
                "active_participants_count": len(active_participants),
                "participants": [
                    {
                        "user_id": participant.user.id,
                        "username": participant.user.username,
                    }
                    for participant in active_participants
                ],
            }
        )

    return Response({"success": True, "rooms": room_data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_call(request, room_id):
    """End a video call and notify all participants"""
    room = get_object_or_404(Room, id=room_id)

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
                    "ended_by_id": request.user.id,
                    "ended_by_username": request.user.username,
                },
            },
        )
    except Exception as e:
        # Don't fail if notification fails
        print(f"Error notifying about call end: {e}")

    return Response({"success": True, "message": "Call ended successfully"})
