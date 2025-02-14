from django.urls import path
from . import views

urlpatterns = [
    path("create-room/", views.create_room, name="create_room"),
    path("join-room/<uuid:room_id>/", views.join_room, name="join_room"),
    path(
        "room-participants/<uuid:room_id>/",
        views.get_room_participants,
        name="room_participants",
    ),
]
