from notifications.models import Notification


def create_notification(*, recipient, actor, notification_type, post=None, comment=None):
    """Create a notification for an interaction.

    Skips self-actions (recipient == actor) so users are never notified
    about their own likes/comments/follows.
    """
    if recipient.pk == actor.pk:
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        post=post,
        comment=comment,
    )


def unread_count(user):
    return Notification.objects.filter(recipient=user, is_read=False).count()


def serialize_notification(notification):
    post = notification.post
    comment = notification.comment
    return {
        "id": notification.id,
        "type": notification.notification_type,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "actor": {
            "id": notification.actor_id,
            "username": notification.actor.username,
            "display_name": notification.actor.display_name or notification.actor.username,
            "profile_picture": (
                notification.actor.profile_picture.url
                if notification.actor.profile_picture
                else None
            ),
        },
        "post": {"id": post.id, "title": post.title} if post else None,
        "comment": {"id": comment.id, "content": comment.content} if comment else None,
    }
