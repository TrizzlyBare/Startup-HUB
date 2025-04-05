import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Participant
from django.contrib.auth import get_user_model
from django.utils import timezone
import asyncio

User = get_user_model()


class VideoCallConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"call_{self.room_id}"
        self.user_specific_group = f"user_{self.user.id}"

        # Check if user is authenticated
        if self.user.is_anonymous:
            await self.close()
            return

        # Check if user is a participant in the room
        is_participant = await self.is_room_participant(self.user.id, self.room_id)
        if not is_participant:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Join user-specific group for targeted notifications
        await self.channel_layer.group_add(self.user_specific_group, self.channel_name)

        await self.accept()

        # Store user presence in Redis with expiration
        await self.update_presence(True)

        # Get current participants
        participants = await self.get_active_participants()

        # Send current participants to the new user
        await self.send_json(
            {"type": "participants_list", "participants": participants}
        )

        # Notify others that user has joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user_id": self.user.id,
                "username": self.user.username,
            },
        )

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "room_group_name"):
            # Update presence status
            await self.update_presence(False)

            # Notify others that user has left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_left",
                    "user_id": self.user.id,
                    "username": self.user.username,
                },
            )

            # Leave groups
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

            await self.channel_layer.group_discard(
                self.user_specific_group, self.channel_name
            )

    async def receive_json(self, content):
        # Handle incoming messages
        message_type = content.get("type")

        # Handle various WebRTC signaling messages
        if message_type == "send_offer":
            # Broadcast offer to all users in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "send_offer",
                    "offer": content["offer"],
                    "sender_id": self.user.id,
                    "sender_username": self.user.username,
                },
            )

        elif message_type == "send_answer":
            # Broadcast answer to all users in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "send_answer",
                    "answer": content["answer"],
                    "sender_id": self.user.id,
                    "sender_username": self.user.username,
                },
            )

        elif message_type == "send_ice_candidate":
            # Broadcast ICE candidate to all users in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "send_ice_candidate",
                    "ice_candidate": content["ice_candidate"],
                    "sender_id": self.user.id,
                },
            )

        # Handle call control messages
        elif message_type == "mute_audio":
            # Update mute status in database
            await self.update_audio_status(content.get("muted", True))

            # Notify others about audio mute status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "audio_status",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "muted": content.get("muted", True),
                },
            )

        elif message_type == "mute_video":
            # Update mute status in database
            await self.update_video_status(content.get("muted", True))

            # Notify others about video mute status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "video_status",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "muted": content.get("muted", True),
                },
            )

        elif message_type == "request_participants":
            # Send current participants list
            participants = await self.get_active_participants()
            await self.send_json(
                {"type": "participants_list", "participants": participants}
            )

        elif message_type == "end_call":
            # End the call for everyone
            await self.end_call()

    # WebRTC signaling handlers
    async def user_joined(self, event):
        # Notify WebSocket about a user joining
        await self.send_json(
            {
                "type": "user_joined",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def user_left(self, event):
        # Notify WebSocket about a user leaving
        await self.send_json(
            {
                "type": "user_left",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def send_offer(self, event):
        # Forward offer to WebSocket
        await self.send_json(
            {
                "type": "offer",
                "offer": event["offer"],
                "sender_id": event["sender_id"],
                "sender_username": event["sender_username"],
            }
        )

    async def send_answer(self, event):
        # Forward answer to WebSocket
        await self.send_json(
            {
                "type": "answer",
                "answer": event["answer"],
                "sender_id": event["sender_id"],
                "sender_username": event["sender_username"],
            }
        )

    async def send_ice_candidate(self, event):
        # Forward ICE candidate to WebSocket
        await self.send_json(
            {
                "type": "ice_candidate",
                "ice_candidate": event["ice_candidate"],
                "sender_id": event["sender_id"],
            }
        )

    # Call control handlers
    async def audio_status(self, event):
        # Forward audio status to WebSocket
        await self.send_json(
            {
                "type": "audio_status",
                "user_id": event["user_id"],
                "username": event["username"],
                "muted": event["muted"],
            }
        )

    async def video_status(self, event):
        # Forward video status to WebSocket
        await self.send_json(
            {
                "type": "video_status",
                "user_id": event["user_id"],
                "username": event["username"],
                "muted": event["muted"],
            }
        )

    # Database access methods
    @database_sync_to_async
    def is_room_participant(self, user_id, room_id):
        """Check if the user is a participant in the room"""
        return Participant.objects.filter(user_id=user_id, room_id=room_id).exists()

    @database_sync_to_async
    def update_audio_status(self, is_muted):
        """Update audio mute status in database"""
        try:
            participant = Participant.objects.get(user=self.user, room_id=self.room_id)
            participant.is_audio_muted = is_muted
            participant.last_active = timezone.now()
            participant.save(update_fields=["is_audio_muted", "last_active"])
        except Participant.DoesNotExist:
            pass

    @database_sync_to_async
    def update_video_status(self, is_muted):
        """Update video mute status in database"""
        try:
            participant = Participant.objects.get(user=self.user, room_id=self.room_id)
            participant.is_video_muted = is_muted
            participant.last_active = timezone.now()
            participant.save(update_fields=["is_video_muted", "last_active"])
        except Participant.DoesNotExist:
            pass

    # Presence methods
    async def update_presence(self, is_online):
        """Update user presence in Redis"""
        # Use Redis channel layer to track presence
        presence_key = f"presence:{self.room_id}:{self.user.id}"

        if is_online:
            # Store presence with 30-second expiration
            await self.update_participant_last_active()

    @database_sync_to_async
    def update_participant_last_active(self):
        """Update the last_active timestamp for the participant"""
        try:
            participant = Participant.objects.get(user=self.user, room_id=self.room_id)
            participant.last_active = timezone.now()
            participant.save(update_fields=["last_active"])
        except Participant.DoesNotExist:
            pass

    @database_sync_to_async
    def get_active_participants(self):
        """Get list of active participants in the room"""
        # Consider participants active if they've been active in the last 30 seconds
        thirty_sec_ago = timezone.now() - timezone.timedelta(seconds=30)
        participants = Participant.objects.filter(
            room_id=self.room_id, last_active__gte=thirty_sec_ago
        ).select_related("user")

        return [
            {
                "user_id": participant.user.id,
                "username": participant.user.username,
                "joined_at": participant.joined_at.isoformat(),
                "is_audio_muted": participant.is_audio_muted,
                "is_video_muted": participant.is_video_muted,
            }
            for participant in participants
        ]

    @database_sync_to_async
    def end_call(self):
        """End the call for all participants"""
        # Get the room
        try:
            room = Room.objects.get(id=self.room_id)

            # Mark room as inactive
            room.is_active = False
            room.save(update_fields=["is_active"])

            # Notify all participants
            asyncio.create_task(
                self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "notification",
                        "message": "video_call_ended",
                        "data": {
                            "video_room_id": str(self.room_id),
                            "ended_by_id": self.user.id,
                            "ended_by_username": self.user.username,
                        },
                    },
                )
            )

            return True
        except Room.DoesNotExist:
            return False
