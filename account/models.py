from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    display_name = models.CharField(
        max_length=100,
        blank=True
    )

    email = models.EmailField(
        unique=True
    )

    biography = models.TextField(
        blank=True,
        default=''
    )

    is_verified = models.BooleanField(
        default=False
    )

    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )

    level = models.PositiveIntegerField(
        default=0
    )

    experience = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.username


class Follow(models.Model):
    follower = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='following_relations'
    )

    following = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='follower_relations'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_follow'
            )
        ]

    def __str__(self):
        return f'{self.follower} follows {self.following}'