from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    slug = models.SlugField(
        max_length=120,
        unique=True,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
    )

    slug = models.SlugField(
        max_length=60,
        unique=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class Post(models.Model):

    class PostType(models.TextChoices):
        PROMPT = "prompt", "Prompt"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )

    post_type = models.CharField(
        max_length=20,
        choices=PostType.choices,
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    prompt = models.TextField(
        blank=True,
        default="",
    )

    image = models.ImageField(
        upload_to="posts/images/",
        blank=True,
        null=True,
        help_text="Generated image attached to an image post.",
    )

    video = models.FileField(
        upload_to="posts/videos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp4", "webm", "mov"])],
        help_text="Generated video attached to a video post.",
    )

    audio = models.FileField(
        upload_to="posts/audio/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["mp3", "wav", "ogg", "m4a"])],
        help_text="Generated audio attached to an audio post.",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="posts",
    )

    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="posts",
    )

    ai_model = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["post_type", "-created_at"],
            ),
            models.Index(
                fields=["category", "-created_at"],
            ),
            models.Index(
                fields=["author", "-created_at"],
            ),
            models.Index(
                fields=["-created_at"],
            ),
        ]

    def __str__(self):
        return self.title
