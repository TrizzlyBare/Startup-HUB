from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Room, Participant
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Room, Participant


@login_required
def create_room(request):
    if request.method == "POST":
        name = request.POST.get("name")
        room = Room.objects.create(name=name)
        Participant.objects.create(user=request.user, room=room)
        return JsonResponse(
            {"success": True, "room_id": str(room.id), "room_name": room.name}
        )
    return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)


@login_required
def join_room(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    participant, created = Participant.objects.get_or_create(
        user=request.user, room=room
    )
    return JsonResponse(
        {"success": True, "room_id": str(room.id), "room_name": room.name}
    )


@login_required
def get_room_participants(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    participants = room.participants.all()
    return JsonResponse(
        {
            "participants": [
                {"id": p.user.id, "username": p.user.username} for p in participants
            ]
        }
    )
