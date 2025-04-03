import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message, Participant, MessageReceipt
from django.contrib.auth import get_user_model
from django.utils import timezone
from uuid import UUID
import asyncio

User = get_user_model()


# Custom JSON encoder to handle UUID serialization
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_{self.room_id}"
        self.user_specific_group = f"user_{self.user.id}"

        # Check if user is participant in this room
        is_participant = await self.is_room_participant(self.user.id, self.room_id)
        if not is_participant:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        # Join user-specific group for targeted notifications
        await self.channel_layer.group_add(self.user_specific_group, self.channel_name)

        await self.accept()

        # Send current online status to the room
        await self.update_user_presence(True)

        # Get and send unread message count
        unread_count = await self.get_unread_count()
        await self.send(
            text_data=json.dumps(
                {
                    "type": "unread.count",
                    "count": unread_count,
                    "room_id": str(self.room_id),
                }
            )
        )

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

            await self.channel_layer.group_discard(
                self.user_specific_group, self.channel_name
            )

            # Send offline status to the room
            await self.update_user_presence(False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "chat.message":
            content = data.get("content", "").strip()
            if content:
                # Save message to database
                message_data = await self.save_message(content)

                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "chat.message", "message": message_data},
                )

        elif message_type == "typing.status":
            # Forward typing status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing.status",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "is_typing": data.get("is_typing", False),
                },
            )

        elif message_type == "mark.read":
            # Mark messages as read
            await self.mark_messages_read()

            # Broadcast read status update
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read.status",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "timestamp": timezone.now().isoformat(),
                },
            )

        elif message_type == "initiate_video_call":
            # User wants to start a video call with room participants
            video_room_id = await self.initiate_video_call()

            # Notify the user about the created room
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "video_call_created",
                        "video_room_id": str(video_room_id),
                        "message_room_id": str(self.room_id),
                    }
                )
            )

        elif message_type == "invite_to_video_call":
            # User wants to invite specific users to a video call
            recipient_id = data.get("recipient_id")
            video_room_id = data.get("video_room_id")

            if recipient_id and video_room_id:
                # Check if recipient is in this chat room
                is_participant = await self.is_user_in_room(recipient_id, self.room_id)
                if is_participant:
                    recipient_username = await self.get_username(recipient_id)

                    # Send invitation to specific user
                    await self.channel_layer.group_send(
                        f"user_{recipient_id}",
                        {
                            "type": "notification",
                            "message": "video_call_invitation",
                            "data": {
                                "video_room_id": video_room_id,
                                "message_room_id": str(self.room_id),
                                "inviter_id": self.user.id,
                                "inviter_username": self.user.username,
                            },
                        },
                    )

                    # Notify room about the invitation
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "notification",
                            "message": "video_call_invitation_sent",
                            "data": {
                                "video_room_id": video_room_id,
                                "message_room_id": str(self.room_id),
                                "inviter_id": self.user.id,
                                "inviter_username": self.user.username,
                                "invited_user_id": recipient_id,
                                "invited_username": recipient_username,
                            },
                        },
                    )

                    # Create a system message about the invitation
                    await self.save_system_message(
                        f"invited {recipient_username} to join a video call"
                    )
                else:
                    # Recipient not in this room
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "error",
                                "message": "The invited user is not a participant in this room",
                            }
                        )
                    )

    async def chat_message(self, event):
        """Handler for chat messages"""
        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {"type": "chat.message", "message": event["message"]}, cls=UUIDEncoder
            )
        )

    async def typing_status(self, event):
        """Handler for typing status updates"""
        # Send typing status to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing.status",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    async def read_status(self, event):
        """Handler for read status updates"""
        # Send read status to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "read.status",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def user_presence(self, event):
        """Handler for user presence updates"""
        # Send presence update to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user.presence",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "is_online": event["is_online"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def notification(self, event):
        """Handler for generic notifications including video calls"""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": event["message"],
                    "data": event["data"],
                },
                cls=UUIDEncoder,
            )
        )

    @database_sync_to_async
    def is_room_participant(self, user_id, room_id):
        """Check if user is a participant in the room"""
        return Participant.objects.filter(user_id=user_id, room_id=room_id).exists()

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database and return serialized data"""
        # Get room
        room = Room.objects.get(id=self.room_id)

        # Create message
        message = Message.objects.create(room=room, sender=self.user, content=content)

        # Create receipts for all other participants
        receipts = []
        participants = Participant.objects.filter(room=room).exclude(user=self.user)
        for participant in participants:
            receipt = MessageReceipt(
                message=message, recipient=participant.user, is_read=False
            )
            receipts.append(receipt)

        if receipts:
            MessageReceipt.objects.bulk_create(receipts)

            # Notify other users about new message
            for participant in participants:
                # This will be processed by Redis channel layer
                asyncio.create_task(
                    self.channel_layer.group_send(
                        f"user_{participant.user.id}",
                        {
                            "type": "notification",
                            "message": "new_message",
                            "data": {
                                "room_id": str(self.room_id),
                                "sender": self.user.username,
                                "message_preview": content[:50]
                                + ("..." if len(content) > 50 else ""),
                            },
                        },
                    )
                )

        # Update room timestamp
        room.save()  # This updates the 'updated_at' field

        # Return serialized message data
        receipt_data = [
            {
                "recipient_id": str(receipt.recipient.id),
                "recipient_username": receipt.recipient.username,
                "is_read": False,
            }
            for receipt in receipts
        ]

        return {
            "id": str(message.id),
            "content": message.content,
            "sender_id": str(message.sender.id),
            "sender_username": message.sender.username,
            "sent_at": message.sent_at.isoformat(),
            "receipts": receipt_data,
            "read_status": {"total": len(receipts), "read": 0, "unread": len(receipts)},
        }

    @database_sync_to_async
    def mark_messages_read(self):
        """Mark all unread messages as read for current user"""
        participant = Participant.objects.get(user=self.user, room_id=self.room_id)
        participant.mark_messages_as_read()
        return True

    async def update_user_presence(self, is_online):
        """Update and broadcast user presence"""
        timestamp = timezone.now().isoformat()

        # Update user's last activity in database
        await self.update_user_last_activity(is_online)

        # Broadcast presence to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user.presence",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "is_online": is_online,
                "timestamp": timestamp,
            },
        )

    @database_sync_to_async
    def update_user_last_activity(self, is_online):
        """Update user's last activity in the participant record"""
        try:
            # Get the actual user ID from the lazy object
            user_id = self.user.id if hasattr(self.user, "id") else None
            if not user_id:
                return

            participant = Participant.objects.get(user_id=user_id, room_id=self.room_id)
            if is_online:
                participant.last_active = timezone.now()
                participant.save(update_fields=["last_active"])
        except Participant.DoesNotExist:
            pass

    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread messages for current user in this room"""
        try:
            participant = Participant.objects.get(user=self.user, room_id=self.room_id)
            return participant.unread_messages_count()
        except Participant.DoesNotExist:
            return 0

    @database_sync_to_async
    def is_user_in_room(self, user_id, room_id):
        """Check if a user is participant in this room"""
        return Participant.objects.filter(user_id=user_id, room_id=room_id).exists()

    @database_sync_to_async
    def get_username(self, user_id):
        """Get a username for a user ID"""
        try:
            user = User.objects.get(id=user_id)
            return user.username
        except User.DoesNotExist:
            return "Unknown User"

    @database_sync_to_async
    def save_system_message(self, content):
        """Save a system message"""
        room = Room.objects.get(id=self.room_id)
        Message.objects.create(room=room, sender=self.user, content=content)

    @database_sync_to_async
    def initiate_video_call(self):
        """Create a video call room linked to this chat room"""
        from webcall.models import Room as VideoRoom, Participant as VideoParticipant

        # Get the chat room
        chat_room = Room.objects.get(id=self.room_id)

        # Create a video call room
        video_room = VideoRoom.objects.create(
            name=f"Call in {chat_room.name}",
            max_participants=20,
            is_recording_enabled=False,
            is_active=True,
        )

        # Add the current user as a participant
        VideoParticipant.objects.create(
            user=self.user, room=video_room, last_active=timezone.now()
        )

        # Create a system message
        Message.objects.create(
            room=chat_room, sender=self.user, content=f"Started a video call"
        )

        # Notify all participants in the chat room
        asyncio.create_task(
            self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "notification",
                    "message": "video_call_started",
                    "data": {
                        "video_room_id": str(video_room.id),
                        "message_room_id": str(self.room_id),
                        "initiator_id": self.user.id,
                        "initiator_username": self.user.username,
                    },
                },
            )
        )

        return video_room.id
    
    # Removed duplicate notification method to resolve errors


class EchoConsumer(WebsocketConsumer):
    channel_layer_alias = None  # Disable channel layer for echo consumer

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        # Simply echo back the received data
        self.send(text_data=text_data)
