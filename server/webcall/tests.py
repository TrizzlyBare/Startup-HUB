from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from channels.testing import WebsocketCommunicator
from server.asgi import application
from webcall.models import Room, Participant
from asgiref.sync import sync_to_async
import json

User = get_user_model()


class WebcallViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser3", password="testinga")
        self.client.login(
            username="testuser3", password="testinga"
        )  # Authenticate the test client
        self.room = Room.objects.create(name="Room1")

    def test_create_room(self):
        response = self.client.post(reverse("create_room"), {"name": "New Room"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Room.objects.filter(name="New Room").exists())

    def test_join_room(self):
        response = self.client.post(reverse("join_room", args=[self.room.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Participant.objects.filter(user=self.user, room=self.room).exists()
        )

    def test_get_room_participants(self):
        Participant.objects.create(user=self.user, room=self.room)
        response = self.client.get(reverse("room_participants", args=[self.room.id]))
        self.assertEqual(response.status_code, 200)
        response_data = response.json()  # Parse the JSON response
        self.assertEqual(len(response_data["participants"]), 1)
        self.assertEqual(response_data["participants"][0]["id"], self.user.id)


class WebcallConsumersTestCase(TestCase):
    async def test_video_call_consumer(self):
        # Create a test user and room
        user = await sync_to_async(User.objects.create_user)(
            username="testuser3", password="testinga"
        )
        room = await sync_to_async(Room.objects.create)(name="Room1")

        # Add the user as a participant in the room
        await sync_to_async(Participant.objects.create)(user=user, room=room)

        # Mock the WebSocket connection with an authenticated user
        communicator = WebsocketCommunicator(application, f"/ws/call/{room.id}/")
        communicator.scope["user"] = user

        # Connect to the WebSocket
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Handle the "user_joined" event
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "user_joined")
        self.assertEqual(response["user_id"], user.id)
        self.assertEqual(response["username"], user.username)

        # Test sending a message
        await communicator.send_json_to({"type": "send_offer", "offer": "test_offer"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "send_offer")
        self.assertEqual(response["offer"], "test_offer")

        # Test disconnect
        await communicator.disconnect()
