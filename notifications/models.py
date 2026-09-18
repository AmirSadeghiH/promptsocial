from django.conf import settings
from django.db import models


class Notification(models.Model):

    class Type(models.TextChoices):
        LIKE = "like", "Like"
        SAVE = "save", "Save"
        COMMENT = "comment", "Comment"
        FOLLOW = "follow", "Follow"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="acted_notifications",
    )

    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )

    comment = models.ForeignKey(
        "interactions.Comment",
        on_delete=models.CASCADE,
        related_name="notifications",
        blank=True,
        null=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.actor} -> {self.recipient} ({self.notification_type})"
