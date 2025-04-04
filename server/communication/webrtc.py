from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.exceptions import DenyConnection
from channels.db import database_sync_to_async
import logging

# Set up logging
logger = logging.getLogger(__name__)


class WebRTCSignalingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.user = self.scope["user"]

            # Ensure user is authenticated
            if not self.user.is_authenticated:
                logger.warning(f"Unauthenticated WebRTC connection attempt")
                raise DenyConnection("Authentication required")

            self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
            self.room_group_name = f"webrtc_{self.room_id}"

            # Record connection for cleanup
            self.connected_groups = set()

            # Verify room participation
            is_participant = await self.is_room_participant()
            if not is_participant:
                logger.warning(
                    f"User {self.user.id} tried to connect to WebRTC for room {self.room_id} without being a participant"
                )
                raise DenyConnection("Not a participant in this room")

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            self.connected_groups.add(self.room_group_name)

            await self.accept()

            # Notify other participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_peer_joined",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                },
            )

            logger.info(f"User {self.user.id} connected to WebRTC room {self.room_id}")
        except DenyConnection as e:
            logger.warning(f"WebRTC connection denied: {str(e)}")
            await self.close()
        except Exception as e:
            logger.error(f"Error in WebRTC connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            # Make sure connected_groups exists
            if not hasattr(self, "connected_groups"):
                self.connected_groups = set()

            # Leave all groups
            for group_name in self.connected_groups:
                await self.channel_layer.group_discard(group_name, self.channel_name)

            # Clear groups set
            self.connected_groups.clear()

            # Make sure room_group_name exists before sending notification
            if hasattr(self, "room_group_name") and hasattr(self, "user"):
                # Notify other participants
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "webrtc_peer_left",
                        "user_id": str(self.user.id),
                        "username": self.user.username,
                    },
                )

                logger.info(
                    f"User {self.user.id} disconnected from WebRTC room {self.room_id}"
                )
        except Exception as e:
            logger.error(f"Error in WebRTC disconnect: {str(e)}")

    async def receive_json(self, content):
        # Handle WebRTC signaling messages
        try:
            message_type = content.get("type")

            if message_type == "offer":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "webrtc_offer",
                        "offer": content["offer"],
                        "sender_id": str(self.user.id),
                    },
                )
            elif message_type == "answer":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "webrtc_answer",
                        "answer": content["answer"],
                        "sender_id": str(self.user.id),
                    },
                )
            elif message_type == "ice_candidate":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "webrtc_ice_candidate",
                        "candidate": content["candidate"],
                        "sender_id": str(self.user.id),
                    },
                )
            else:
                logger.warning(f"Unknown WebRTC message type: {message_type}")
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )
        except KeyError as e:
            logger.error(f"Missing field in WebRTC message: {str(e)}")
            await self.send_json(
                {"type": "error", "message": f"Missing field: {str(e)}"}
            )
        except Exception as e:
            logger.error(f"Error processing WebRTC message: {str(e)}")
            await self.send_json(
                {"type": "error", "message": "Failed to process message"}
            )

    # Database Sync Methods
    @database_sync_to_async
    def is_room_participant(self):
        from .models import Participant

        return Participant.objects.filter(room_id=self.room_id, user=self.user).exists()

    # WebSocket Event Handlers
    async def webrtc_offer(self, event):
        # Don't send the offer back to the sender
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "offer",
                    "offer": event["offer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def webrtc_answer(self, event):
        # Don't send the answer back to the sender
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "answer",
                    "answer": event["answer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def webrtc_ice_candidate(self, event):
        # Don't send the ICE candidate back to the sender
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "ice_candidate",
                    "candidate": event["candidate"],
                    "sender_id": event["sender_id"],
                }
            )

    async def webrtc_peer_joined(self, event):
        # Don't send the notification back to the joiner
        if str(self.user.id) != event["user_id"]:
            await self.send_json(
                {
                    "type": "peer_joined",
                    "user_id": event["user_id"],
                    "username": event["username"],
                }
            )

    async def webrtc_peer_left(self, event):
        # Don't need to check if it's the sender since they've already disconnected
        await self.send_json(
            {
                "type": "peer_left",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )
