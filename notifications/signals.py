from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from interactions.models import Comment, Follow, Like, Save
from notifications.services import create_notification


@receiver(post_save, sender=Like)
def notify_on_like(sender, instance, created, **kwargs):
    if created:
        create_notification(
            recipient=instance.post.author,
            actor=instance.user,
            notification_type="like",
            post=instance.post,
        )


@receiver(post_delete, sender=Like)
def cleanup_on_unlike(sender, instance, **kwargs):
    if instance.post_id and instance.user_id:
        from notifications.models import Notification

        Notification.objects.filter(
            recipient_id=instance.post.author_id,
            actor_id=instance.user_id,
            notification_type="like",
            post_id=instance.post_id,
        ).delete()


@receiver(post_save, sender=Save)
def notify_on_save(sender, instance, created, **kwargs):
    if created:
        create_notification(
            recipient=instance.post.author,
            actor=instance.user,
            notification_type="save",
            post=instance.post,
        )


@receiver(post_save, sender=Comment)
def notify_on_comment(sender, instance, created, **kwargs):
    if created:
        create_notification(
            recipient=instance.post.author,
            actor=instance.user,
            notification_type="comment",
            post=instance.post,
            comment=instance,
        )


@receiver(post_save, sender=Follow)
def notify_on_follow(sender, instance, created, **kwargs):
    if created:
        create_notification(
            recipient=instance.following,
            actor=instance.follower,
            notification_type="follow",
        )
