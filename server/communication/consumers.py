from asyncio.log import logger
import json
import base64
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from django.utils import timezone
from .utils import MediaProcessor
import functools
from django.core.cache import cache

# Add these imports at the top of the file
from django.contrib.auth import get_user_model
from .models import Room, Participant, Message

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import logging
import json
import base64
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import Room, Participant, Message
from .utils import MediaProcessor
from django.core.cache import cache
from django.db.models import Q

logger = logging.getLogger(__name__)

User = get_user_model()


class CommunicationConsumer(AsyncJsonWebsocketConsumer):
    # async def connect(self):
    #     self.user = self.scope["user"]
    #     self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
    #     self.room_group_name = f"room_{self.room_id}"
    #     self.user_group_name = f"user_{self.user.id}"

    #     # Verify room participation
    #     is_participant = await self.is_room_participant()
    #     if not is_participant:
    #         await self.close()
    #         return

    #     # Join room and user groups
    #     await self.channel_layer.group_add(self.room_group_name, self.channel_name)
    #     await self.channel_layer.group_add(self.user_group_name, self.channel_name)

    #     await self.accept()
    #     await self.update_user_presence(True)

    async def connect(self):
        # Extract username from route
        username = self.scope["url_route"]["kwargs"].get("username")

        User = get_user_model()
        try:
            # Find user by username
            user = await self.get_user_by_username(username)

            if not user:
                await self.close()
                return

            # Set user in scope
            self.scope["user"] = user
            self.user = user

            # Proceed with room setup
            await self.setup_room(username)

            await self.accept()

        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.close()

    @database_sync_to_async
    def setup_room(self, username):
        # Find or create direct message room
        other_user = get_user_model().objects.get(username=username)

        # Ensure consistent room naming
        room_name = sorted([self.user.username, username])
        room_name = f"Chat between {room_name[0]} and {room_name[1]}"

        room, created = Room.objects.get_or_create(name=room_name, room_type="direct")

        # Ensure participants exist
        Participant.objects.get_or_create(user=self.user, room=room)
        Participant.objects.get_or_create(user=other_user, room=room)

        self.room_id = str(room.id)
        self.room_group_name = f"room_{self.room_id}"

        # Join room group
        return self.channel_layer.group_add(self.room_group_name, self.channel_name)

    @database_sync_to_async
    def get_user_by_username(self, username):
        User = get_user_model()
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    async def disconnect(self, close_code):
        # Leave groups
        if hasattr(self, "room_group_name") and hasattr(self, "channel_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

        if hasattr(self, "user_group_name") and hasattr(self, "channel_name"):
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )

        # Update user presence
        await self.update_user_presence(False)

    @database_sync_to_async
    def setup_room(self, username):
        # Find or create direct message room
        room, created = Room.objects.get_or_create(
            name=f"Chat between {self.user.username} and {username}", room_type="direct"
        )

        # Ensure participants exist
        other_user = get_user_model().objects.get(username=username)

        Participant.objects.get_or_create(user=self.user, room=room)
        Participant.objects.get_or_create(user=other_user, room=room)

        self.room_id = str(room.id)
        self.room_group_name = f"room_{self.room_id}"

        # Join room group
        return self.channel_layer.group_add(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        message_type = content.get("type")

        try:
            if message_type == "text_message":
                await self.handle_text_message(content)
            elif message_type == "image_message":
                await self.handle_image_message(content)
            elif message_type == "video_message":
                await self.handle_video_message(content)
            elif message_type == "audio_message":
                await self.handle_audio_message(content)
            elif message_type == "typing":
                await self.handle_typing_status(content)
            elif message_type == "start_call":
                await self.handle_start_call(content)
            elif message_type == "call_response":
                await self.handle_call_response(content)
            elif message_type == "webrtc_offer":
                await self.handle_webrtc_offer(content)
            elif message_type == "webrtc_answer":
                await self.handle_webrtc_answer(content)
            elif message_type == "ice_candidate":
                await self.handle_ice_candidate(content)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )
        except Exception as e:
            logger.error(f"Error processing {message_type} message: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

            try:
                # Try to send error to client but don't raise more exceptions
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Error processing {message_type} message: {str(e)}",
                    }
                )
            except Exception as inner_e:
                logger.error(f"Failed to send error message: {str(inner_e)}")

    async def handle_text_message(self, content):
        if not self.room_id:
            await self.send_json({"type": "error", "message": "No room_id specified"})
            return

        message = await self.save_message(
            content=content.get("content"), message_type="text"
        )
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    async def handle_image_message(self, content):
        # Base64 image handling
        image_data = content.get("image")
        if not image_data or ";" not in image_data or "base64," not in image_data:
            await self.send_json(
                {"type": "error", "message": "Invalid image data format"}
            )
            return

        try:
            image_format, image_str = image_data.split(";base64,")
            ext = image_format.split("/")[-1]

            decoded_image = base64.b64decode(image_str)

            # Upload to Cloudinary
            image_url = await self.upload_image(
                ContentFile(decoded_image, name=f"image.{ext}")
            )

            if not image_url:
                await self.send_json(
                    {"type": "error", "message": "Failed to upload image"}
                )
                return

            message = await self.save_message(
                content=content.get("caption", ""),
                message_type="image",
                image=image_url,
            )

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in handle_image_message: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_video_message(self, content):
        try:
            # Base64 video handling
            video_data = content.get("video")
            if not video_data or ";" not in video_data or "base64," not in video_data:
                await self.send_json(
                    {"type": "error", "message": "Invalid video data format"}
                )
                return

            video_format, video_str = video_data.split(";base64,")
            ext = video_format.split("/")[-1]

            decoded_video = base64.b64decode(video_str)

            # Upload to Cloudinary
            video_upload = await self.upload_video(
                ContentFile(decoded_video, name=f"video.{ext}")
            )

            # Check if upload was successful
            if not video_upload:
                await self.send_json(
                    {"type": "error", "message": "Failed to upload video"}
                )
                return

            message = await self.save_message(
                content=video_upload.get("thumbnail_url", ""),
                message_type="video",
                video=video_upload.get("video_url"),
            )

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in handle_video_message: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_audio_message(self, content):
        try:
            # Base64 audio handling
            audio_data = content.get("audio")
            if not audio_data or ";" not in audio_data or "base64," not in audio_data:
                await self.send_json(
                    {"type": "error", "message": "Invalid audio data format"}
                )
                return

            audio_format, audio_str = audio_data.split(";base64,")
            ext = audio_format.split("/")[-1]

            decoded_audio = base64.b64decode(audio_str)

            # Upload to Cloudinary
            audio_url = await self.upload_audio(
                ContentFile(decoded_audio, name=f"audio.{ext}")
            )

            if not audio_url:
                await self.send_json(
                    {"type": "error", "message": "Failed to upload audio"}
                )
                return

            message = await self.save_message(
                content="Audio Message", message_type="audio", audio=audio_url
            )

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in handle_audio_message: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_typing_status(self, content):
        is_typing = content.get("is_typing", False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_status",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "is_typing": is_typing,
            },
        )

    async def handle_start_call(self, content):
        call_type = content.get("call_type", "video")
        message = await self.save_call_message(call_type=call_type, status="initiated")

        await self.channel_layer.group_send(
            self.room_group_name, {"type": "call_notification", "call": message}
        )

    async def handle_call_response(self, content):
        invitation_id = content.get("invitation_id")
        response = content.get("response")  # 'accept' or 'decline'

        invitation_update = await self.process_call_invitation_response(
            invitation_id, response
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "call_response",
                "invitation_id": invitation_id,
                "response": response,
                "user_id": str(self.user.id),
                "username": self.user.username,
            },
        )

    # WebRTC Signaling Methods
    async def handle_webrtc_offer(self, content):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_offer",
                "offer": content["offer"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_webrtc_answer(self, content):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_answer",
                "answer": content["answer"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_ice_candidate(self, content):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "ice_candidate",
                "candidate": content["candidate"],
                "sender_id": str(self.user.id),
            },
        )

    # # Database Sync Methods
    # @database_sync_to_async
    # def is_room_participant(self):
    #     from .models import Participant

    #     return Participant.objects.filter(room_id=self.room_id, user=self.user).exists()
    @database_sync_to_async
    def is_room_participant(self):
        from .models import Participant, Room

        try:
            # Check if room exists and user is a participant
            room = Room.objects.get(id=self.room_id)
            return Participant.objects.filter(room=room, user=self.user).exists()
        except Room.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, message_type, image=None, video=None, audio=None):
        from .models import Message, Room

        if not self.room_id:
            logger.error("Attempted to save message without room_id")
            return None

        try:
            # Verify room exists
            room = Room.objects.get(id=self.room_id)

            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                message_type=message_type,
                image=image,
                video=video,
                audio=audio,
            )
            return {
                "id": str(message.id),
                "content": message.content,
                "sender_id": str(message.sender.id),
                "sender": {
                    "id": str(message.sender.id),
                    "username": message.sender.username,
                },
                "message_type": message.message_type,
                "image": message.image,
                "video": message.video,
                "audio": message.audio,
                "sent_at": message.sent_at.isoformat(),
                "room_id": str(message.room.id),
            }
        except Room.DoesNotExist:
            logger.error(f"Room with id {self.room_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

    @database_sync_to_async
    def update_user_presence(self, is_online):
        from .models import Participant

        try:
            participant = Participant.objects.get(room_id=self.room_id, user=self.user)
            participant.last_active = timezone.now() if is_online else None
            participant.save(update_fields=["last_active"])
        except Participant.DoesNotExist:
            logger.warning(
                f"Participant not found for user {self.user.id} in room {self.room_id}"
            )
        except Exception as e:
            logger.error(f"Error updating presence: {str(e)}")

    @database_sync_to_async
    def upload_image(self, image_file):
        from .utils import MediaProcessor

        try:
            return MediaProcessor.upload_image(image_file)
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            return None

    @database_sync_to_async
    def upload_video(self, video_file):
        from .utils import MediaProcessor

        try:
            return MediaProcessor.upload_video(video_file)
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            return None

    @database_sync_to_async
    def upload_audio(self, audio_file):
        from .utils import MediaProcessor

        try:
            return MediaProcessor.upload_audio(audio_file)
        except Exception as e:
            logger.error(f"Error uploading audio: {str(e)}")
            return None

    @database_sync_to_async
    def save_call_message(self, call_type, status):
        from .models import Message, Room

        message = Message.objects.create(
            room_id=self.room_id,
            sender=self.user,
            message_type="call",
            call_type=call_type,
            call_status=status,
        )
        return {
            "id": str(message.id),
            "call_type": call_type,
            "status": status,
            "sender_id": str(message.sender.id),
            "sender": {
                "id": str(message.sender.id),
                "username": message.sender.username,
            },
            "sent_at": message.sent_at.isoformat(),
        }

    @database_sync_to_async
    def process_call_invitation_response(self, invitation_id, response):
        from .models import CallInvitation

        try:
            invitation = CallInvitation.objects.get(id=invitation_id)
            invitation.status = "accepted" if response == "accept" else "declined"
            invitation.save(update_fields=["status"])

            return {
                "inviter_id": str(invitation.inviter.id),
                "video_room_id": str(invitation.room.id),
            }
        except CallInvitation.DoesNotExist:
            logger.error(f"Call invitation {invitation_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error processing call invitation: {str(e)}")
            return None

    # WebSocket Event Handlers
    async def chat_message(self, event):
        message = event["message"]

        # Add sender information if not already included
        if "sender" not in message and "sender_id" in message:
            try:
                # Use cached user info
                sender_id = message["sender_id"]
                user_info = await self.get_cached_user_info(sender_id)
                if user_info:
                    message["sender"] = user_info
            except Exception as e:
                logger.error(f"Error getting user info: {str(e)}")

        await self.send_json({"type": "chat_message", "message": message})

    async def typing_status(self, event):
        await self.send_json(
            {
                "type": "typing_status",
                "user_id": event["user_id"],
                "username": event["username"],
                "is_typing": event["is_typing"],
            }
        )

    async def call_notification(self, event):
        await self.send_json({"type": "call_notification", "call": event["call"]})

    async def call_response(self, event):
        await self.send_json(
            {
                "type": "call_response",
                "invitation_id": event["invitation_id"],
                "response": event["response"],
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def participant_added(self, event):
        await self.send_json(
            {"type": "participant_added", "participant": event["participant"]}
        )

    async def webrtc_offer(self, event):
        await self.send_json(
            {
                "type": "webrtc_offer",
                "offer": event["offer"],
                "sender_id": event["sender_id"],
            }
        )

    async def webrtc_answer(self, event):
        await self.send_json(
            {
                "type": "webrtc_answer",
                "answer": event["answer"],
                "sender_id": event["sender_id"],
            }
        )

    async def ice_candidate(self, event):
        await self.send_json(
            {
                "type": "ice_candidate",
                "candidate": event["candidate"],
                "sender_id": event["sender_id"],
            }
        )

    async def call_invitation(self, event):
        await self.send_json(
            {"type": "call_invitation", "invitation": event["invitation"]}
        )

    # Cache helper method
    @database_sync_to_async
    def get_cached_user_info(self, user_id):
        """Get cached user information to reduce database queries"""
        cache_key = f"user_info_{user_id}"
        user_info = cache.get(cache_key)
        if not user_info:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                user_info = {
                    "id": str(user.id),
                    "username": user.username,
                }
                cache.set(cache_key, user_info, 300)  # Cache for 5 minutes
            except User.DoesNotExist:
                logger.error(f"User {user_id} not found")
                return None
            except Exception as e:
                logger.error(f"Error getting user info: {str(e)}")
                return None
        return user_info


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Unified WebSocket consumer that supports both room-based and username-based connections
    """

    async def connect(self):
        """
        Handle WebSocket connection for both connection types
        """
        try:
            # Get the authenticated user from the scope
            self.user = self.scope["user"]

            # Check if user is authenticated
            if not self.user or not self.user.is_authenticated:
                logger.warning("Unauthenticated connection attempt")
                await self.close(code=4003)  # Authentication failure
                return

            # Determine the connection type based on URL parameters
            if "room_id" in self.scope["url_route"]["kwargs"]:
                await self.setup_room_connection()
            elif "username" in self.scope["url_route"]["kwargs"]:
                await self.setup_username_connection()
            else:
                logger.error("No room_id or username specified in URL route")
                await self.close(code=4004)  # Missing identifier
                return

            # Accept the WebSocket connection
            await self.accept()

            # Update user's presence status
            await self.update_user_presence(True)

            # Notify other room participants about the new connection
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_joined",
                    "user_id": str(self.user.id),
                    "username": self.user.username,
                },
            )

            logger.info(
                f"User {self.user.id} connected to {self.connection_type} {self.identifier}"
            )

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close(code=4000)  # Generic error

    async def setup_room_connection(self):
        """Configure a room-based connection"""
        self.connection_type = "room"
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.identifier = self.room_id

        # Set up room group name
        self.room_group_name = f"room_{self.room_id}"
        self.user_group_name = f"user_{self.user.id}"

        # Verify user is a participant in the room
        is_participant = await self.is_room_participant(self.room_id)
        if not is_participant:
            logger.warning(
                f"User {self.user.id} attempted to join room {self.room_id} without being a participant"
            )
            await self.close(code=4005)  # Not a participant
            return

        # Join groups
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

    async def setup_username_connection(self):
        """Configure a username-based connection"""
        self.connection_type = "username"
        self.target_username = self.scope["url_route"]["kwargs"]["username"]
        self.identifier = self.target_username

        # Find or create direct message room between the users
        room_data = await self.setup_direct_room(self.target_username)
        if not room_data:
            logger.error(
                f"Could not setup direct room with user {self.target_username}"
            )
            await self.close(code=4006)  # Failed to set up room
            return

        # Set room ID and group names
        self.room_id = room_data["room_id"]
        self.room_group_name = f"room_{self.room_id}"
        self.user_group_name = f"user_{self.user.id}"

        # Join groups
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        try:
            # Leave groups if they exist
            if hasattr(self, "room_group_name") and hasattr(self, "channel_name"):
                await self.channel_layer.group_discard(
                    self.room_group_name, self.channel_name
                )

            if hasattr(self, "user_group_name") and hasattr(self, "channel_name"):
                await self.channel_layer.group_discard(
                    self.user_group_name, self.channel_name
                )

            # Update user presence status if we have the necessary attributes
            if hasattr(self, "user") and hasattr(self, "room_id"):
                await self.update_user_presence(False)

                # Notify other participants about the disconnection
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_left",
                        "user_id": str(self.user.id),
                        "username": self.user.username,
                    },
                )

            logger.info(
                f"User {getattr(self, 'user', 'unknown')} disconnected from {getattr(self, 'connection_type', 'unknown')} {getattr(self, 'identifier', 'unknown')}"
            )

        except Exception as e:
            logger.error(f"Disconnect error: {str(e)}")

    async def receive_json(self, content):
        """
        Handle received WebSocket messages
        """
        message_type = content.get("type")

        try:
            # Handle different message types
            if message_type == "text_message":
                await self.handle_text_message(content)
            elif message_type == "image_message":
                await self.handle_image_message(content)
            elif message_type == "video_message":
                await self.handle_video_message(content)
            elif message_type == "audio_message":
                await self.handle_audio_message(content)
            elif message_type == "typing":
                await self.handle_typing_status(content)
            elif message_type == "start_call":
                await self.handle_start_call(content)
            elif message_type == "call_response":
                await self.handle_call_response(content)
            elif message_type == "webrtc_offer":
                await self.handle_webrtc_offer(content)
            elif message_type == "webrtc_answer":
                await self.handle_webrtc_answer(content)
            elif message_type == "ice_candidate":
                await self.handle_ice_candidate(content)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )
        except Exception as e:
            logger.error(f"Error processing {message_type} message: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

            try:
                # Send error to client
                await self.send_json(
                    {
                        "type": "error",
                        "message": f"Error processing {message_type} message: {str(e)}",
                    }
                )
            except Exception as inner_e:
                logger.error(f"Failed to send error message: {str(inner_e)}")

    # Database access methods
    @database_sync_to_async
    def is_room_participant(self, room_id):
        """
        Check if the current user is a participant in the specified room
        """
        try:
            # Verify room exists and user is a participant
            return Participant.objects.filter(room_id=room_id, user=self.user).exists()
        except Exception as e:
            logger.error(f"Error checking room participation: {str(e)}")
            return False

    @database_sync_to_async
    def setup_direct_room(self, username):
        """
        Find or create a direct message room between current user and target user
        """
        try:
            # Find target user
            target_user = User.objects.get(username=username)

            # Ensure consistent room naming
            sorted_usernames = sorted([self.user.username, username])
            room_name = f"Chat between {sorted_usernames[0]} and {sorted_usernames[1]}"

            # Find or create the room
            room, created = Room.objects.get_or_create(
                name=room_name, room_type="direct"
            )

            # Ensure both users are participants
            Participant.objects.get_or_create(user=self.user, room=room)
            Participant.objects.get_or_create(user=target_user, room=room)

            return {
                "room_id": str(room.id),
                "other_user_id": str(target_user.id),
                "created": created,
            }
        except User.DoesNotExist:
            logger.error(f"User {username} not found")
            return None
        except Exception as e:
            logger.error(f"Error setting up direct room: {str(e)}")
            return None

    @database_sync_to_async
    def update_user_presence(self, is_online):
        """
        Update user's presence status in the room
        """
        try:
            participant = Participant.objects.get(room_id=self.room_id, user=self.user)

            participant.last_active = timezone.now() if is_online else None
            participant.save(update_fields=["last_active"])

            return True
        except Participant.DoesNotExist:
            logger.warning(
                f"Participant not found for user {self.user.id} in room {self.room_id}"
            )
            return False
        except Exception as e:
            logger.error(f"Error updating presence: {str(e)}")
            return False

    @database_sync_to_async
    def save_message(self, content, message_type, image=None, video=None, audio=None):
        """
        Save a message to the database
        """
        try:
            # Verify room exists
            room = Room.objects.get(id=self.room_id)

            # Create message
            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content,
                message_type=message_type,
                image=image,
                video=video,
                audio=audio,
            )

            # Return serialized message data
            return {
                "id": str(message.id),
                "content": message.content,
                "sender_id": str(message.sender.id),
                "sender": {
                    "id": str(message.sender.id),
                    "username": message.sender.username,
                },
                "message_type": message.message_type,
                "image": message.image,
                "video": message.video,
                "audio": message.audio,
                "sent_at": message.sent_at.isoformat(),
                "room_id": str(message.room.id),
            }
        except Room.DoesNotExist:
            logger.error(f"Room with id {self.room_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

    @database_sync_to_async
    def save_call_message(self, call_type, status):
        """
        Save call notification message
        """
        try:
            room = Room.objects.get(id=self.room_id)

            message = Message.objects.create(
                room=room,
                sender=self.user,
                message_type="call",
                call_type=call_type,
                call_status=status,
            )
            return {
                "id": str(message.id),
                "call_type": call_type,
                "status": status,
                "sender_id": str(message.sender.id),
                "sender": {
                    "id": str(message.sender.id),
                    "username": message.sender.username,
                },
                "sent_at": message.sent_at.isoformat(),
            }
        except Room.DoesNotExist:
            logger.error(f"Room with id {self.room_id} does not exist")
            return None
        except Exception as e:
            logger.error(f"Error saving call message: {str(e)}")
            return None

    @database_sync_to_async
    def process_call_invitation_response(self, invitation_id, response):
        """Process response to a call invitation"""
        from .models import CallInvitation

        try:
            invitation = CallInvitation.objects.get(id=invitation_id)
            invitation.status = "accepted" if response == "accept" else "declined"
            invitation.save(update_fields=["status"])

            return {
                "inviter_id": str(invitation.inviter.id),
                "video_room_id": str(invitation.room.id),
            }
        except CallInvitation.DoesNotExist:
            logger.error(f"Call invitation {invitation_id} not found")
            return None
        except Exception as e:
            logger.error(f"Error processing call invitation: {str(e)}")
            return None

    @database_sync_to_async
    def upload_image(self, image_file):
        """Upload image to Cloudinary"""
        from .utils import MediaProcessor

        try:
            return MediaProcessor.upload_image(image_file)
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            return None

    @database_sync_to_async
    def upload_video(self, video_file):
        """Upload video to Cloudinary"""
        from .utils import MediaProcessor

        try:
            return MediaProcessor.upload_video(video_file)
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            return None

    @database_sync_to_async
    def upload_audio(self, audio_file):
        """Upload audio to Cloudinary"""
        from .utils import MediaProcessor

        try:
            return MediaProcessor.upload_audio(audio_file)
        except Exception as e:
            logger.error(f"Error uploading audio: {str(e)}")
            return None

    # Message handlers
    async def handle_text_message(self, content):
        """
        Handle text message
        """
        message = await self.save_message(
            content=content.get("content"), message_type="text"
        )

        if message:
            # Broadcast message to room
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        else:
            await self.send_json({"type": "error", "message": "Failed to save message"})

    async def handle_image_message(self, content):
        """Handle image messages"""
        # Base64 image handling
        image_data = content.get("image")
        if not image_data or ";" not in image_data or "base64," not in image_data:
            await self.send_json(
                {"type": "error", "message": "Invalid image data format"}
            )
            return

        try:
            image_format, image_str = image_data.split(";base64,")
            ext = image_format.split("/")[-1]

            decoded_image = base64.b64decode(image_str)

            # Upload to Cloudinary
            image_url = await self.upload_image(
                ContentFile(decoded_image, name=f"image.{ext}")
            )

            if not image_url:
                await self.send_json(
                    {"type": "error", "message": "Failed to upload image"}
                )
                return

            message = await self.save_message(
                content=content.get("caption", ""),
                message_type="image",
                image=image_url,
            )

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in handle_image_message: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_video_message(self, content):
        """Handle video messages"""
        try:
            # Base64 video handling
            video_data = content.get("video")
            if not video_data or ";" not in video_data or "base64," not in video_data:
                await self.send_json(
                    {"type": "error", "message": "Invalid video data format"}
                )
                return

            video_format, video_str = video_data.split(";base64,")
            ext = video_format.split("/")[-1]

            decoded_video = base64.b64decode(video_str)

            # Upload to Cloudinary
            video_upload = await self.upload_video(
                ContentFile(decoded_video, name=f"video.{ext}")
            )

            # Check if upload was successful
            if not video_upload:
                await self.send_json(
                    {"type": "error", "message": "Failed to upload video"}
                )
                return

            message = await self.save_message(
                content=video_upload.get("thumbnail_url", ""),
                message_type="video",
                video=video_upload.get("video_url"),
            )

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in handle_video_message: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_audio_message(self, content):
        """Handle audio messages"""
        try:
            # Base64 audio handling
            audio_data = content.get("audio")
            if not audio_data or ";" not in audio_data or "base64," not in audio_data:
                await self.send_json(
                    {"type": "error", "message": "Invalid audio data format"}
                )
                return

            audio_format, audio_str = audio_data.split(";base64,")
            ext = audio_format.split("/")[-1]

            decoded_audio = base64.b64decode(audio_str)

            # Upload to Cloudinary
            audio_url = await self.upload_audio(
                ContentFile(decoded_audio, name=f"audio.{ext}")
            )

            if not audio_url:
                await self.send_json(
                    {"type": "error", "message": "Failed to upload audio"}
                )
                return

            message = await self.save_message(
                content="Audio Message", message_type="audio", audio=audio_url
            )

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", "message": message}
            )
        except Exception as e:
            logger.error(f"Error in handle_audio_message: {str(e)}")
            await self.send_json({"type": "error", "message": str(e)})

    async def handle_typing_status(self, content):
        """
        Handle typing status updates
        """
        is_typing = content.get("is_typing", False)

        # Broadcast typing status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_status",
                "user_id": str(self.user.id),
                "username": self.user.username,
                "is_typing": is_typing,
            },
        )

    async def handle_start_call(self, content):
        """Handle call initiation"""
        call_type = content.get("call_type", "video")
        message = await self.save_call_message(call_type=call_type, status="initiated")

        await self.channel_layer.group_send(
            self.room_group_name, {"type": "call_notification", "call": message}
        )

    async def handle_call_response(self, content):
        """Handle response to call invitation"""
        invitation_id = content.get("invitation_id")
        response = content.get("response")  # 'accept' or 'decline'

        invitation_update = await self.process_call_invitation_response(
            invitation_id, response
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "call_response",
                "invitation_id": invitation_id,
                "response": response,
                "user_id": str(self.user.id),
                "username": self.user.username,
            },
        )

    # WebRTC Signaling Methods
    async def handle_webrtc_offer(self, content):
        """Handle WebRTC offer"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_offer",
                "offer": content["offer"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_webrtc_answer(self, content):
        """Handle WebRTC answer"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "webrtc_answer",
                "answer": content["answer"],
                "sender_id": str(self.user.id),
            },
        )

    async def handle_ice_candidate(self, content):
        """Handle ICE candidate"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "ice_candidate",
                "candidate": content["candidate"],
                "sender_id": str(self.user.id),
            },
        )

    # WebSocket Event Handlers
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        message = event["message"]

        # Add sender information if not already included
        if "sender" not in message and "sender_id" in message:
            try:
                # Use cached user info
                sender_id = message["sender_id"]
                user_info = await self.get_cached_user_info(sender_id)
                if user_info:
                    message["sender"] = user_info
            except Exception as e:
                logger.error(f"Error getting user info: {str(e)}")

        await self.send_json({"type": "chat_message", "message": message})

    async def typing_status(self, event):
        """Send typing status to WebSocket"""
        await self.send_json(
            {
                "type": "typing_status",
                "user_id": event["user_id"],
                "username": event["username"],
                "is_typing": event["is_typing"],
            }
        )

    async def call_notification(self, event):
        """Send call notification to WebSocket"""
        await self.send_json({"type": "call_notification", "call": event["call"]})

    async def call_response(self, event):
        """Send call response to WebSocket"""
        await self.send_json(
            {
                "type": "call_response",
                "invitation_id": event["invitation_id"],
                "response": event["response"],
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def user_joined(self, event):
        """Send user joined notification to WebSocket"""
        # Don't send to the user who joined
        if str(self.user.id) != event["user_id"]:
            await self.send_json(
                {
                    "type": "user_joined",
                    "user_id": event["user_id"],
                    "username": event["username"],
                }
            )

    async def user_left(self, event):
        """Send user left notification to WebSocket"""
        # Don't need to check since the disconnected user won't receive this
        await self.send_json(
            {
                "type": "user_left",
                "user_id": event["user_id"],
                "username": event["username"],
            }
        )

    async def webrtc_offer(self, event):
        """Send WebRTC offer to WebSocket"""
        # Don't send back to sender
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "webrtc_offer",
                    "offer": event["offer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def webrtc_answer(self, event):
        """Send WebRTC answer to WebSocket"""
        # Don't send back to sender
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "webrtc_answer",
                    "answer": event["answer"],
                    "sender_id": event["sender_id"],
                }
            )

    async def ice_candidate(self, event):
        """Send ICE candidate to WebSocket"""
        # Don't send back to sender
        if str(self.user.id) != event["sender_id"]:
            await self.send_json(
                {
                    "type": "ice_candidate",
                    "candidate": event["candidate"],
                    "sender_id": event["sender_id"],
                }
            )

    # Cache helper method
    @database_sync_to_async
    def get_cached_user_info(self, user_id):
        """Get cached user information to reduce database queries"""
        cache_key = f"user_info_{user_id}"
        user_info = cache.get(cache_key)
        if not user_info:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                user_info = {
                    "id": str(user.id),
                    "username": user.username,
                }
                cache.set(cache_key, user_info, 300)  # Cache for 5 minutes
            except User.DoesNotExist:
                logger.error(f"User {user_id} not found")
                return None
            except Exception as e:
                logger.error(f"Error getting user info: {str(e)}")
                return None
        return user_info

    # Add these new methods to the ChatConsumer class

    async def room_call_announcement(self, event):
        """Send room call announcement notification to WebSocket"""
        await self.send_json(
            {"type": "room_call_announcement", "notification": event["notification"]}
        )

    # Enhance the existing handle_incoming_call_status method
    async def handle_incoming_call_status(self, content):
        """Handle updates to incoming call notifications"""
        notification_id = content.get("notification_id")
        status = content.get("status")

        if not notification_id or not status:
            await self.send_json(
                {"type": "error", "message": "notification_id and status are required"}
            )
            return

        if status not in ["seen", "accepted", "declined", "missed", "ended"]:
            await self.send_json(
                {
                    "type": "error",
                    "message": f"Invalid status: {status}. Must be one of: seen, accepted, declined, missed, ended",
                }
            )
            return

        # Update notification status in database
        notification = await self.update_call_notification_status(
            notification_id, status
        )

        if notification:
            # Notify caller about status update
            caller_group_name = f"user_{notification['caller_id']}"
            await self.channel_layer.group_send(
                caller_group_name,
                {"type": "call_notification_update", "notification": notification},
            )

            # If accepted, notify room about call being answered
            if status == "accepted":
                room_id = notification["room_id"]
                call_message = await self.create_call_answered_message(
                    room_id, notification["caller_id"], notification["call_type"]
                )

                if call_message:
                    room_group_name = f"room_{room_id}"
                    await self.channel_layer.group_send(
                        room_group_name,
                        {"type": "call_notification", "call": call_message},
                    )

            # If ended, notify about call ending
            if status == "ended":
                room_id = notification["room_id"]
                # Update call message in database
                call_message = await self.update_call_ended_message(
                    room_id, notification["caller_id"], notification["call_type"]
                )

                if call_message:
                    room_group_name = f"room_{room_id}"
                    await self.channel_layer.group_send(
                        room_group_name, {"type": "call_ended", "call": call_message}
                    )
        else:
            await self.send_json(
                {
                    "type": "error",
                    "message": f"Failed to update notification {notification_id}",
                }
            )

    # Add new helper method for ending calls
    @database_sync_to_async
    def update_call_ended_message(self, room_id, caller_id, call_type):
        """Update call message when a call is ended"""
        from .models import Message, Room
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        User = get_user_model()

        try:
            room = Room.objects.get(id=room_id)
            caller = User.objects.get(id=caller_id)

            # Find the most recent answered call message
            call_message = (
                Message.objects.filter(
                    room=room,
                    sender=caller,
                    message_type="call",
                    call_type=call_type,
                    call_status="answered",
                )
                .order_by("-sent_at")
                .first()
            )

            if call_message:
                # Calculate duration
                duration = int((timezone.now() - call_message.sent_at).total_seconds())
                call_message.call_duration = duration
                call_message.call_status = "ended"
                call_message.save()

                return {
                    "id": str(call_message.id),
                    "room_id": str(call_message.room.id),
                    "sender_id": str(call_message.sender.id),
                    "sender": {
                        "id": str(call_message.sender.id),
                        "username": call_message.sender.username,
                    },
                    "message_type": "call",
                    "call_type": call_type,
                    "call_status": "ended",
                    "call_duration": duration,
                    "sent_at": call_message.sent_at.isoformat(),
                }
            return None
        except (Room.DoesNotExist, User.DoesNotExist) as e:
            logger.error(f"Room or user not found: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error ending call message: {str(e)}")
            return None

    @database_sync_to_async
    def update_call_notification_status(self, notification_id, status):
        """Update incoming call notification status"""
        from .models import IncomingCallNotification

        try:
            # The error is here - fix the query structure to avoid positional args after keyword args
            # The problem is likely in how you're constructing the filter conditions

            # First get the notification by ID
            try:
                notification = IncomingCallNotification.objects.get(id=notification_id)

                # Then check permissions separately
                if notification.recipient != self.user:
                    # Allow caller to update only for 'ended' status
                    if (
                        notification.caller != self.user
                        or status != "ended"
                        or notification.status != "accepted"
                    ):
                        logger.warning(
                            f"User {self.user.id} not authorized to update notification {notification_id}"
                        )
                        return None

                # Check if expired
                old_status = notification.status
                if notification.is_expired() and status not in ["missed", "ended"]:
                    notification.status = "expired"
                else:
                    notification.status = status

                notification.save()

                logger.info(
                    f"Updated call notification {notification_id} status from {old_status} to {status}"
                )

                # Return serialized notification
                return {
                    "id": str(notification.id),
                    "caller_id": str(notification.caller.id),
                    "caller_username": notification.caller.username,
                    "recipient_id": str(notification.recipient.id),
                    "recipient_username": notification.recipient.username,
                    "room_id": str(notification.room.id),
                    "room_name": notification.room.name,
                    "call_type": notification.call_type,
                    "status": notification.status,
                    "created_at": notification.created_at.isoformat(),
                    "expires_at": notification.expires_at.isoformat(),
                }
            except IncomingCallNotification.DoesNotExist:
                logger.warning(f"Notification {notification_id} not found")
                return None

        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")
            return None
