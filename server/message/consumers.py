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

        # Fetch online participants
        participants = await self.get_online_participants()
        await self.send(
            text_data=json.dumps(
                {"type": "participants.list", "participants": participants},
                cls=UUIDEncoder,
            )
        )

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

            # Leave user-specific group
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
            # Store typing status in Redis with expiration
            is_typing = data.get("is_typing", False)
            if is_typing:
                # Set typing status with 3-second expiration
                await self.set_typing_status(is_typing)

            # Forward typing status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing.status",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                    "is_typing": is_typing,
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

        elif message_type == "fetch.history":
            # Fetch chat history with pagination
            before_id = data.get("before_id")
            limit = data.get("limit", 20)

            history = await self.get_message_history(before_id, limit)

            await self.send(
                text_data=json.dumps(
                    {
                        "type": "chat.history",
                        "messages": history,
                        "room_id": str(self.room_id),
                    },
                    cls=UUIDEncoder,
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
        """Handler for user notifications"""
        # Send notification to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": event["message"],
                    "data": event.get("data", {}),
                }
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
                            "message": "New message",
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

    async def set_typing_status(self, is_typing):
        """Store typing status in Redis with expiration"""
        # Using Redis channel layer to store ephemeral data
        channel_name = f"typing:{self.room_id}:{self.user.id}"

        if is_typing:
            # This will be automatically cleaned up by Redis after 3 seconds
            await self.channel_layer.send(
                channel_name, {"type": "typing_indicator", "is_typing": True}
            )

    @database_sync_to_async
    def get_unread_count(self):
        """Get count of unread messages for current user in this room"""
        try:
            participant = Participant.objects.get(user=self.user, room_id=self.room_id)
            return participant.unread_messages_count()
        except Participant.DoesNotExist:
            return 0

    @database_sync_to_async
    def get_message_history(self, before_id=None, limit=20):
        """Get paginated message history"""
        query = Message.objects.filter(room_id=self.room_id)

        if before_id:
            try:
                before_message = Message.objects.get(id=before_id)
                query = query.filter(sent_at__lt=before_message.sent_at)
            except (Message.DoesNotExist, ValueError):
                pass

        messages = (
            query.select_related("sender")
            .prefetch_related("receipts__recipient")
            .order_by("-sent_at")[:limit]
        )

        # Convert to list of dictionaries
        result = []
        for message in messages:
            receipts_data = [
                {
                    "recipient_id": str(receipt.recipient.id),
                    "recipient_username": receipt.recipient.username,
                    "is_read": receipt.is_read,
                }
                for receipt in message.receipts.all()
            ]

            total = len(receipts_data)
            read = sum(1 for r in receipts_data if r["is_read"])

            result.append(
                {
                    "id": str(message.id),
                    "content": message.content,
                    "sender_id": str(message.sender.id),
                    "sender_username": message.sender.username,
                    "sent_at": message.sent_at.isoformat(),
                    "receipts": receipts_data,
                    "read_status": {
                        "total": total,
                        "read": read,
                        "unread": total - read,
                    },
                }
            )

        return result

    @database_sync_to_async
    def get_online_participants(self):
        """Get list of online participants"""
        # Online participants are those who have been active in the last 5 minutes
        five_min_ago = timezone.now() - timezone.timedelta(minutes=5)
        participants = Participant.objects.filter(
            room_id=self.room_id, last_active__gte=five_min_ago
        ).select_related("user")

        return [
            {
                "user_id": str(participant.user.id),
                "username": participant.user.username,
                "last_active": (
                    participant.last_active.isoformat()
                    if participant.last_active
                    else None
                ),
            }
            for participant in participants
        ]


class EchoConsumer(WebsocketConsumer):
    channel_layer_alias = None  # Disable channel layer for echo consumer

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        # Simply echo back the received data
        self.send(text_data=text_data)
