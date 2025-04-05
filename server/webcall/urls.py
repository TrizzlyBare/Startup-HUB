from django.urls import path
from . import views

urlpatterns = [
    path("create-room/", views.create_room, name="create_room"),
    path("join-room/<uuid:room_id>/", views.join_room, name="join_room"),
    path("leave-room/<uuid:room_id>/", views.leave_room, name="leave_room"),
    path(
        "room-participants/<uuid:room_id>/",
        views.get_room_participants,
        name="room_participants",
    ),
    path(
        "media-status/<uuid:room_id>/",
        views.update_media_status,
        name="update_media_status",
    ),
    path("end-call/<uuid:room_id>/", views.end_call, name="end_call"),
    path("active-calls/", views.active_calls, name="active_calls"),
]
