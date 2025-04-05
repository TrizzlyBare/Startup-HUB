# views.py
from .models import Message, Channel
from .serializers import MessageSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class MessageViewSet(ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    @action(detail=False, methods=["POST"])
    def create_message(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["GET"])
    def get_messages_by_channel(self, request):
        channel_id = request.query_params.get("channel_id")
        if channel_id is None:
            return Response(
                {"error": "Channel ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            Channel.objects.get(id=channel_id)
        except Channel.DoesNotExist:
            return Response(
                {"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND
            )

        messages = Message.objects.filter(channel_id=channel_id).order_by("created_at")
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
