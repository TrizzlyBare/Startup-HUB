# webrtc_consumer.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from .models import Room, Participant
import logging
import json
import uuid

logger = logging.getLogger(__name__)
User = get_user_model()


class WebRTCSignalingConsumer(AsyncJsonWebsocketConsumer):
    """
    Advanced WebRTC Signaling Consumer for real-time communication
    """

    async def connect(self):
        """
        Handle WebSocket connection with robust authentication and room management
        """
        try:
            # Extract room ID from URL
            self.room_id = self.scope["url_route"]["kwargs"]["room_id"]

            # Authenticate user
            self.user = await self.get_authenticated_user()

            if not self.user:
                logger.warning("Unauthenticated WebRTC connection attempt")
                await self.close(code=4003)  # Authentication failure
                return

            # Verify room participation
            is_participant = await self.is_room_participant()
            if not is_participant:
                logger.warning(
                    f"User {self.user.id} not a participant in room {self.room_id}"
                )
                await self.close(code=4005)  # Not a participant
                return

            # Create room-specific group name
            self.room_group_name = f"webrtc_{self.room_id}"

            # Add to channel layer group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            # Accept WebSocket connection
            await self.accept()

            # Notify other participants about new peer
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "peer_joined",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                },
            )

            logger.info(f"User {self.user.id} connected to WebRTC room {self.room_id}")

        except Exception as e:
            logger.error(f"WebRTC connection error: {str(e)}")
            await self.close(code=4000)  # Generic error

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        try:
            # Notify room about peer leaving
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "peer_left",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                },
            )

            # Remove from channel layer group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

            logger.info(
                f"User {self.user.id} disconnected from WebRTC room {self.room_id}"
            )

        except Exception as e:
            logger.error(f"Disconnect error: {str(e)}")

    async def receive_json(self, content):
        """
        Handle incoming WebRTC signaling messages
        """
        try:
            message_type = content.get("type")

            # Routing for different signaling message types
            signaling_handlers = {
                "offer": self.handle_offer,
                "answer": self.handle_answer,
                "ice_candidate": self.handle_ice_candidate,
                "screen_share": self.handle_screen_share,
            }

            handler = signaling_handlers.get(message_type)
            if handler:
                await handler(content)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

        except Exception as e:
            logger.error(f"Signaling message error: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_offer(self, content):
        """
        Forward WebRTC offer to other participants
        """
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_offer",
                "offer": content["offer"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_answer(self, content):
        """
        Forward WebRTC answer to other participants
        """
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_answer",
                "answer": content["answer"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_ice_candidate(self, content):
        """
        Forward ICE candidate to other participants
        """
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_ice_candidate",
                "candidate": content["candidate"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_screen_share(self, content):
        """
        Handle screen sharing initiation
        """
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "screen_share",
                "sender_id": str(self.user.id),
                "is_sharing": content.get("is_sharing", False),
            },
        )

    # WebSocket Event Handlers
    async def webrtc_offer(self, event):
        """Send WebRTC offer to client"""
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "offer",
                    "offer": event["offer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def webrtc_answer(self, event):
        """Send WebRTC answer to client"""
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "answer",
                    "answer": event["answer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def webrtc_ice_candidate(self, event):
        """Send ICE candidate to client"""
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "ice_candidate",
                    "candidate": event["candidate"],
                    "sender_id": event["sender_id"],
                }
            )

    async def peer_joined(self, event):
        """Notify about peer joining"""
        if str(self.user.id) != event["user_id"]:
            await self.send_json(
                {
                    "type": "peer_joined",
                    "user_id": event["user_id"],
                    "username": event["username"],
                }
            )

    async def peer_left(self, event):
        """Notify about peer leaving"""
        await self.send_json(
            {
                "type": "peer_left",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    # Database Access Methods
    @database_sync_to_async
    def get_authenticated_user(self):
        """
        Authenticate user from WebSocket scope
        """
        # Extract authentication token from query params or headers
        token_key = self.scope.get("query_string", b"").decode().split("=")[-1]

        try:
            # Validate token
            token = Token.objects.get(key=token_key)
            return token.user
        except (Token.DoesNotExist, ValueError):
            logger.warning("Invalid or missing authentication token")
            return None

    @database_sync_to_async
    def is_room_participant(self):
        """
        Check if user is a participant in the room
        """
        try:
            # Verify room exists and user is a participant
            room = Room.objects.get(id=self.room_id)
            return Participant.objects.filter(room=room, user=self.user).exists()
        except Room.DoesNotExist:
            logger.error(f"Room {self.room_id} does not exist")
            return False
