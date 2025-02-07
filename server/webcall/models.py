from django.db import models


class WebRTCSession(models.Model):
    room = models.CharField(max_length=100, unique=True)
    offer = models.TextField(null=True, blank=True)
    answer = models.TextField(null=True, blank=True)
    ice_candidates = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.room
