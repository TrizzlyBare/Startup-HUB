from django.urls import path
from . import views

urlpatterns = [
    path(
        "messages/",
        views.MessageViewSet.as_view({"get": "list", "post": "create"}),
        name="message-list",
    ),
    path(
        "messages/<uuid:pk>/",
        views.MessageViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="message-detail",
    ),
    path(
        "messages/by-channel/",
        views.MessageViewSet.as_view({"get": "get_messages_by_channel"}),
        name="messages-by-channel",
    ),
]
