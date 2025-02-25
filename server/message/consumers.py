import json
from channels.generic.websocket import AsyncWebsocketConsumer
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
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user_id = self.scope["user"].id

        # Save message to database
        saved_message = await self.save_message(user_id, message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'user_id': user_id,
                'message_id': saved_message.id,
                'timestamp': saved_message.sent_at.isoformat()
            }
        )

    async def chat_message(self, event):
        """Handler for chat messages"""
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'user_id': event['user_id'],
            'message_id': event['message_id'],
            'timestamp': event['timestamp']
        }))

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
    def save_message(self, user_id, message_content):
        """Save message to database and return serialized data"""
        user = User.objects.get(id=user_id)
        room = Room.objects.get(id=self.room_id)
        message = Message.objects.create(
            sender=user,
            room=room,
            content=message_content
        )
        
        # Create message receipts for all participants except sender
        participants = room.participants.exclude(user=user)
        MessageReceipt.objects.bulk_create([
            MessageReceipt(message=message, recipient=participant.user)
            for participant in participants
        ])
        
        # Update room timestamp
        room.save()  # This updates the 'updated_at' field

        # Return serialized message data
        return message

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
