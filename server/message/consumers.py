import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message, Participant, MessageReceipt
from django.contrib.auth import get_user_model
from django.utils import timezone
from uuid import UUID

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

        # Check if user is participant in this room
        is_participant = await self.is_room_participant(self.user.id, self.room_id)
        if not is_participant:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Send current online status to the room
        await self.update_user_presence(True)

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
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
            participant = Participant.objects.get(user=self.user, room_id=self.room_id)
            if is_online:
                # Update some field to track when user was last active
                participant.last_active = timezone.now()
                participant.save(update_fields=["last_active"])
        except Participant.DoesNotExist:
            pass


class EchoConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        # Simply echo back the received data
        self.send(text_data=text_data)
