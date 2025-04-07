from django.conf import settings
from django.utils import timezone


class WebRTCConfig:
    @staticmethod
    def get_ice_servers():
        """
        Generate ICE server configuration for WebRTC
        """
        ice_servers = [
            # Public STUN servers
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
        ]

        # Optional: Add TURN servers from settings
        turn_servers = getattr(settings, "WEBRTC_TURN_SERVERS", [])
        ice_servers.extend(turn_servers)

        return ice_servers

    @staticmethod
    def get_media_constraints():
        """
        Default media constraints for WebRTC
        """
        return {
            "audio": {
                "echoCancellation": True,
                "noiseSuppression": True,
                "autoGainControl": True,
            },
            "video": {
                "width": {"ideal": 1280, "max": 1920},
                "height": {"ideal": 720, "max": 1080},
                "frameRate": {"ideal": 30, "max": 60},
            },
        }

    @staticmethod
    def is_webrtc_supported(user_agent=None):
        """
        Check WebRTC browser compatibility
        Optional user agent check can be added
        """
        # Implement browser compatibility checks if needed
        return True

    @staticmethod
    def generate_webrtc_token(user, room):
        """
        Generate a temporary token for WebRTC session
        """
        from django.contrib.auth.tokens import default_token_generator

        return default_token_generator.make_token(user)
