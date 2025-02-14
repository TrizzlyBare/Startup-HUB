from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Participant
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class VideoCallConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"call_{self.room_id}"

        # Check if user is authenticated
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        # Check if user is a participant in the room
        is_participant = await self.is_room_participant(
            self.scope["user"].id, self.room_id
        )
        if not is_participant:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Notify others that user has joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user_id": self.scope["user"].id,
                "username": self.scope["user"].username,
            },
        )

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_left",
                    "user_id": self.scope["user"].id,
                    "username": self.scope["user"].username,
                },
            )
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def receive_json(self, content):
        message_type = content.get("type")

        if message_type == "offer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "send_offer",
                    "offer": content["offer"],
                    "sender_id": self.scope["user"].id,
                    "receiver_id": content["receiver_id"],
                },
            )

        elif message_type == "answer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "send_answer",
                    "answer": content["answer"],
                    "sender_id": self.scope["user"].id,
                    "receiver_id": content["receiver_id"],
                },
            )

        elif message_type == "ice_candidate":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "send_ice_candidate",
                    "ice_candidate": content["ice_candidate"],
                    "sender_id": self.scope["user"].id,
                    "receiver_id": content["receiver_id"],
                },
            )

    async def user_joined(self, event):
        await self.send_json(
            {
                "type": "user_joined",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def user_left(self, event):
        await self.send_json(
            {
                "type": "user_left",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def send_offer(self, event):
        if str(self.scope["user"].id) == str(event["receiver_id"]):
            await self.send_json(
                {
                    "type": "offer",
                    "offer": event["offer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def send_answer(self, event):
        if str(self.scope["user"].id) == str(event["receiver_id"]):
            await self.send_json(
                {
                    "type": "answer",
                    "answer": event["answer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def send_ice_candidate(self, event):
        if str(self.scope["user"].id) == str(event["receiver_id"]):
            await self.send_json(
                {
                    "type": "ice_candidate",
                    "ice_candidate": event["ice_candidate"],
                    "sender_id": event["sender_id"],
                }
            )

    @database_sync_to_async
    def is_room_participant(self, user_id, room_id):
        try:
            participant = Participant.objects.get(user_id=user_id, room_id=room_id)
            return True
        except Participant.DoesNotExist:
            return False
