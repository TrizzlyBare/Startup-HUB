from channels.generic.websocket import AsyncJsonWebsocketConsumer


class WebRTCSignalingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"webrtc_{self.room_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content):
        # Handle WebRTC signaling messages
        message_type = content.get("type")

        if message_type == "offer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_offer",
                    "offer": content["offer"],
                    "sender_id": content["sender_id"],
                },
            )
        elif message_type == "answer":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_answer",
                    "answer": content["answer"],
                    "sender_id": content["sender_id"],
                },
            )
        elif message_type == "ice_candidate":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "webrtc_ice_candidate",
                    "candidate": content["candidate"],
                    "sender_id": content["sender_id"],
                },
            )

    # WebSocket Event Handlers
    async def webrtc_offer(self, event):
        await self.send_json(
            {"type": "offer", "offer": event["offer"], "sender_id": event["sender_id"]}
        )

    async def webrtc_answer(self, event):
        await self.send_json(
            {
                "type": "answer",
                "answer": event["answer"],
                "sender_id": event["sender_id"],
            }
        )

    async def webrtc_ice_candidate(self, event):
        await self.send_json(
            {
                "type": "ice_candidate",
                "candidate": event["candidate"],
                "sender_id": event["sender_id"],
            }
        )
