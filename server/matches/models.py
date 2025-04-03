from django.db import models
from django.conf import settings
from django.utils import timezone
from authen.models import CustomUser


class Match(models.Model):
    """
    Model to store matches between users
    """

    user = models.ForeignKey(
        CustomUser,
        related_name="initiated_matches",
        on_delete=models.CASCADE,
        help_text="User who initiated the match",
    )
    matched_user = models.ForeignKey(
        CustomUser,
        related_name="received_matches",
        on_delete=models.CASCADE,
        help_text="User who was matched with",
    )
    created_at = models.DateTimeField(default=timezone.now)
    is_mutual = models.BooleanField(
        default=False, help_text="True if both users have matched with each other"
    )

    class Meta:
        unique_together = ("user", "matched_user")
        verbose_name = "Match"
        verbose_name_plural = "Matches"

    def __str__(self):
        mutual_status = "mutual" if self.is_mutual else "pending"
        return f"{self.user.username} → {self.matched_user.username} ({mutual_status})"


class Like(models.Model):
    """
    Model to store user likes (swipes right)
    """

    user = models.ForeignKey(
        CustomUser,
        related_name="likes_given",
        on_delete=models.CASCADE,
        help_text="User who gave the like",
    )
    liked_user = models.ForeignKey(
        CustomUser,
        related_name="likes_received",
        on_delete=models.CASCADE,
        help_text="User who received the like",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "liked_user")
        verbose_name = "Like"
        verbose_name_plural = "Likes"

    def __str__(self):
        return f"{self.user.username} likes {self.liked_user.username}"


class Dislike(models.Model):
    """
    Model to store user dislikes (swipes left)
    """

    user = models.ForeignKey(
        CustomUser,
        related_name="dislikes_given",
        on_delete=models.CASCADE,
        help_text="User who gave the dislike",
    )
    disliked_user = models.ForeignKey(
        CustomUser,
        related_name="dislikes_received",
        on_delete=models.CASCADE,
        help_text="User who received the dislike",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "disliked_user")
        verbose_name = "Dislike"
        verbose_name_plural = "Dislikes"

    def __str__(self):
        return f"{self.user.username} dislikes {self.disliked_user.username}"
