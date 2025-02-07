from rest_framework import serializers
from .models import WebRTCSession


class WebRTCSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebRTCSession
        fields = "__all__"
