import json
import logging
from collections import defaultdict
import reflex as rx

# Set up logging
logger = logging.getLogger(__name__)

class SignalingState(rx.State):
    """State for WebRTC signaling."""
    
    # Store rooms and their participants
    rooms: dict = {}
    
    # Store pending offers, answers, and ICE candidates
    pending_offers: dict = {}
    pending_answers: dict = {}
    pending_ice_candidates: dict = {}
    
    def join_room(self, room_id: str, user_id: str, username: str):
        """Join a room."""
        if room_id not in self.rooms:
            self.rooms[room_id] = []
        
        # Check if user is already in the room
        for participant in self.rooms[room_id]:
            if participant["user_id"] == user_id:
                return
        
        # Add user to the room
        self.rooms[room_id].append({
            "user_id": user_id,
            "username": username
        })
        
        print(f"User {username} ({user_id}) joined room {room_id}")
    
    def leave_room(self, room_id: str, user_id: str):
        """Leave a room."""
        if room_id in self.rooms:
            self.rooms[room_id] = [
                p for p in self.rooms[room_id] if p["user_id"] != user_id
            ]
            
            # Remove the room if empty
            if not self.rooms[room_id]:
                del self.rooms[room_id]
    
    def get_room_participants(self, room_id: str):
        """Get all participants in a room except the current user."""
        return self.rooms.get(room_id, [])
    
    def send_offer(self, offer, receiver_id: str, sender_id: str):
        """Send an offer to a specific user."""
        key = f"{receiver_id}"
        if key not in self.pending_offers:
            self.pending_offers[key] = []
        
        self.pending_offers[key].append({
            "sender_id": sender_id,
            "offer": offer
        })
    
    def get_pending_offers(self, user_id: str):
        """Get all pending offers for a user."""
        key = f"{user_id}"
        offers = self.pending_offers.get(key, [])
        
        # Clear pending offers
        if key in self.pending_offers:
            del self.pending_offers[key]
        
        return offers
    
    def send_answer(self, answer, receiver_id: str, sender_id: str):
        """Send an answer to a specific user."""
        key = f"{receiver_id}"
        if key not in self.pending_answers:
            self.pending_answers[key] = []
        
        self.pending_answers[key].append({
            "sender_id": sender_id,
            "answer": answer
        })
    
    def get_pending_answers(self, user_id: str):
        """Get all pending answers for a user."""
        key = f"{user_id}"
        answers = self.pending_answers.get(key, [])
        
        # Clear pending answers
        if key in self.pending_answers:
            del self.pending_answers[key]
        
        return answers
    
    def send_ice_candidate(self, candidate, receiver_id: str, sender_id: str):
        """Send an ICE candidate to a specific user."""
        key = f"{receiver_id}"
        if key not in self.pending_ice_candidates:
            self.pending_ice_candidates[key] = []
        
        self.pending_ice_candidates[key].append({
            "sender_id": sender_id,
            "candidate": candidate
        })
    
    def get_pending_ice_candidates(self, user_id: str):
        """Get all pending ICE candidates for a user."""
        key = f"{user_id}"
        candidates = self.pending_ice_candidates.get(key, [])
        
        # Clear pending candidates
        if key in self.pending_ice_candidates:
            del self.pending_ice_candidates[key]
        
        return candidates

# Create an instance to use in the app
webrtc_socket_handler = SignalingState 