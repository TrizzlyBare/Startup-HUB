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


class CommunicationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"room_{self.room_id}"
        self.user_group_name = f"user_{self.user.id}"

        # Verify room participation
        is_participant = await self.is_room_participant()
        if not is_participant:
            await self.close()
            return

        # Join room and user groups
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()
        await self.update_user_presence(True)

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

    # Database Sync Methods
    @database_sync_to_async
    def is_room_participant(self):
        from .models import Participant

        return Participant.objects.filter(room_id=self.room_id, user=self.user).exists()

    @database_sync_to_async
    def save_message(self, content, message_type, image=None, video=None, audio=None):
        from .models import Message, Room

        message = Message.objects.create(
            room_id=self.room_id,
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
        }

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
