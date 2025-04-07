import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from communication.webrtc_config import WebRTCConfig


class WebRTCConfigTests(unittest.TestCase):
    """Test WebRTC configuration functionality without database dependencies"""

    def test_ice_servers_configuration(self):
        """Test that ICE servers are correctly configured"""
        ice_servers = WebRTCConfig.get_ice_servers()

        # Verify STUN servers exist
        stun_servers = [server for server in ice_servers if "stun:" in server["urls"]]
        self.assertTrue(len(stun_servers) > 0, "STUN servers should be configured")

        # Check if Google STUN server is included
        google_stun = next(
            (server for server in ice_servers if "stun.l.google.com" in server["urls"]),
            None,
        )
        self.assertIsNotNone(google_stun, "Google STUN server should be configured")

    def test_media_constraints(self):
        """Test that media constraints are correctly configured"""
        constraints = WebRTCConfig.get_media_constraints()

        # Verify audio constraints
        self.assertIn("audio", constraints, "Audio constraints should be configured")
        self.assertTrue(
            constraints["audio"]["echoCancellation"],
            "Echo cancellation should be enabled",
        )
        self.assertTrue(
            constraints["audio"]["noiseSuppression"],
            "Noise suppression should be enabled",
        )

        # Verify video constraints
        self.assertIn("video", constraints, "Video constraints should be configured")
        self.assertIn("width", constraints["video"], "Video width should be configured")
        self.assertIn(
            "height", constraints["video"], "Video height should be configured"
        )
        self.assertIn(
            "frameRate", constraints["video"], "Frame rate should be configured"
        )

    def test_webrtc_support_detection(self):
        """Test WebRTC browser compatibility detection"""
        # Test default case (no user agent)
        is_supported = WebRTCConfig.is_webrtc_supported()
        self.assertTrue(is_supported, "WebRTC should be supported by default")

        # Test with a modern browser user agent
        chrome_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        is_supported = WebRTCConfig.is_webrtc_supported(chrome_user_agent)
        self.assertTrue(is_supported, "WebRTC should be supported in Chrome")

    @patch("django.contrib.auth.tokens.default_token_generator.make_token")
    def test_webrtc_token_generation(self, mock_make_token):
        """Test WebRTC token generation"""
        mock_make_token.return_value = "test_token"

        # Create mock user and room
        mock_user = MagicMock()
        mock_room = MagicMock()

        # Generate token
        token = WebRTCConfig.generate_webrtc_token(mock_user, mock_room)

        # Verify token generation
        self.assertEqual(
            token, "test_token", "WebRTC token should be generated correctly"
        )
        mock_make_token.assert_called_once_with(mock_user)


if __name__ == "__main__":
    unittest.main()
