from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_relations'
    )

    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower_relations'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_user_follow",
            ),
        ]
        indexes = [
            models.Index(
                fields=["follower", "-created_at"],
            ),
            models.Index(
                fields=["following", "-created_at"],
            ),
        ]

    def clean(self):
        if self.follower == self.following:
            raise ValidationError("Users cannot follow themselves.")

    def __str__(self):
        return f"{self.follower} follows {self.following}"



class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )

    post = models.ForeignKey(
        'posts.Post',
        on_delete=models.CASCADE,
        related_name='likes'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_user_post_like",
            ),
        ]
        indexes = [
            models.Index(
                fields=["post", "-created_at"],
            ),
        ]

    def __str__(self):
        return f"{self.user} likes {self.post}"



class Save(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_posts'
    )

    post = models.ForeignKey(
        'posts.Post',
        on_delete=models.CASCADE,
        related_name='saves'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_user_post_save",
            ),
        ]
        indexes = [

            models.Index(
                fields=["user", "-created_at"],
            ),

            models.Index(
                fields=["post", "-created_at"],
            ),
        ]

    def __str__(self):
        return f"{self.user} saved {self.post}"



class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="comments",
    )

    content = models.TextField(
        max_length=2000,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["post", "created_at"],
            ),
        ]

    def __str__(self):
        return f"{self.user} on {self.post}"