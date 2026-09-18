from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from interactions.models import Comment, Follow, Like, PostCopy, PostView, Save
from posts.models import Category, Post


def _make_post(author, title="A useful prompt"):
    category, _ = Category.objects.get_or_create(name="Writing", slug="writing")
    return Post.objects.create(
        author=author,
        category=category,
        post_type=Post.PostType.PROMPT,
        title=title,
    )


class PostEngagementModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="event-user",
            email="event-user@example.com",
            password="test-password",
        )
        self.post = _make_post(self.user)

    def test_view_can_be_recorded_without_a_user(self):
        event = PostView.objects.create(post=self.post)

        self.assertIsNone(event.user)
        self.assertEqual(event.post, self.post)

    def test_copy_records_each_use_by_the_same_user(self):
        PostCopy.objects.create(post=self.post, user=self.user)
        PostCopy.objects.create(post=self.post, user=self.user)

        self.assertEqual(
            PostCopy.objects.filter(post=self.post, user=self.user).count(),
            2,
        )


class PostEngagementApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="api-user",
            email="api-user@example.com",
            password="test-password",
        )
        self.post = _make_post(self.user, "An API prompt")

    def test_anonymous_post_creates_a_view_event(self):
        response = self.client.post(
            reverse("interactions:record-view", args=[self.post.pk]),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"post_id": self.post.pk, "event": "view"},
        )
        self.assertTrue(
            PostView.objects.filter(post=self.post, user__isnull=True).exists(),
        )

    def test_authenticated_post_records_the_viewing_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("interactions:record-view", args=[self.post.pk]),
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            PostView.objects.filter(post=self.post, user=self.user).exists(),
        )

    def test_anonymous_user_cannot_record_a_copy(self):
        response = self.client.post(
            reverse("interactions:record-copy", args=[self.post.pk]),
        )

        self.assertEqual(response.status_code, 302)  # login redirect
        self.assertEqual(PostCopy.objects.count(), 0)

    def test_authenticated_user_can_record_a_copy(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("interactions:record-copy", args=[self.post.pk]),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {"post_id": self.post.pk, "event": "copy"},
        )
        self.assertTrue(PostCopy.objects.filter(post=self.post, user=self.user).exists())

    def test_event_endpoints_return_not_found_for_unknown_post(self):
        response = self.client.post(reverse("interactions:record-view", args=[9999]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "Post not found."})

    def test_event_endpoints_reject_non_post_requests(self):
        response = self.client.get(
            reverse("interactions:record-view", args=[self.post.pk]),
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"error": "Method not allowed."})


class ToggleLikeApiTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username="like-author",
            email="like-author@example.com",
            password="test-password",
        )
        self.fan = get_user_model().objects.create_user(
            username="like-fan",
            email="like-fan@example.com",
            password="test-password",
        )
        self.post = _make_post(self.author, "Like me")

    def test_requires_authentication(self):
        response = self.client.post(reverse("interactions:toggle-like", args=[self.post.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_then_unlike_roundtrip(self):
        self.client.force_login(self.fan)

        liked = self.client.post(reverse("interactions:toggle-like", args=[self.post.pk]))
        self.assertEqual(liked.status_code, 201)
        self.assertTrue(liked.json()["liked"])
        self.assertEqual(liked.json()["like_count"], 1)

        unliked = self.client.post(reverse("interactions:toggle-like", args=[self.post.pk]))
        self.assertEqual(unliked.status_code, 200)
        self.assertFalse(unliked.json()["liked"])
        self.assertEqual(unliked.json()["like_count"], 0)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_returns_404_for_unknown_post(self):
        self.client.force_login(self.fan)

        response = self.client.post(reverse("interactions:toggle-like", args=[9999]))

        self.assertEqual(response.status_code, 404)


class ToggleSaveApiTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username="save-author",
            email="save-author@example.com",
            password="test-password",
        )
        self.fan = get_user_model().objects.create_user(
            username="save-fan",
            email="save-fan@example.com",
            password="test-password",
        )
        self.post = _make_post(self.author, "Save me")

    def test_save_then_unsave_roundtrip(self):
        self.client.force_login(self.fan)

        saved = self.client.post(reverse("interactions:toggle-save", args=[self.post.pk]))
        self.assertEqual(saved.status_code, 201)
        self.assertTrue(saved.json()["saved"])

        unsaved = self.client.post(reverse("interactions:toggle-save", args=[self.post.pk]))
        self.assertEqual(unsaved.status_code, 200)
        self.assertFalse(unsaved.json()["saved"])
        self.assertEqual(Save.objects.count(), 0)


class CommentApiTests(TestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username="comment-author",
            email="comment-author@example.com",
            password="test-password",
        )
        self.fan = get_user_model().objects.create_user(
            username="comment-fan",
            email="comment-fan@example.com",
            password="test-password",
        )
        self.post = _make_post(self.author, "Comment on me")

    def test_anonymous_users_cannot_comment(self):
        response = self.client.post(
            reverse("interactions:create-comment", args=[self.post.pk]),
            {"content": "hi"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_authenticated_user_can_comment_and_list(self):
        self.client.force_login(self.fan)

        created = self.client.post(
            reverse("interactions:create-comment", args=[self.post.pk]),
            {"content": "Amazing prompt!"},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["content"], "Amazing prompt!")

        listed = self.client.get(reverse("interactions:list-comments", args=[self.post.pk]))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["results"]), 1)

    def test_empty_comment_is_rejected(self):
        self.client.force_login(self.fan)

        response = self.client.post(
            reverse("interactions:create-comment", args=[self.post.pk]),
            {"content": "   "},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_commenter_can_delete_own_comment_but_not_others(self):
        own_comment = Comment.objects.create(post=self.post, user=self.fan, content="mine")
        foreign_comment = Comment.objects.create(post=self.post, user=self.author, content="theirs")

        self.client.force_login(self.fan)
        forbidden = self.client.delete(
            reverse("interactions:delete-comment", args=[foreign_comment.pk])
        )
        self.assertEqual(forbidden.status_code, 403)

        allowed = self.client.delete(
            reverse("interactions:delete-comment", args=[own_comment.pk])
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(Comment.objects.count(), 1)

    def test_post_author_can_moderate_comments(self):
        comment = Comment.objects.create(post=self.post, user=self.fan, content="spam")

        self.client.force_login(self.author)
        response = self.client.delete(reverse("interactions:delete-comment", args=[comment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 0)


class ToggleFollowApiTests(TestCase):
    def setUp(self):
        self.target = get_user_model().objects.create_user(
            username="follow-target",
            email="follow-target@example.com",
            password="test-password",
        )
        self.fan = get_user_model().objects.create_user(
            username="follow-fan",
            email="follow-fan@example.com",
            password="test-password",
        )

    def test_follow_then_unfollow_roundtrip(self):
        self.client.force_login(self.fan)

        followed = self.client.post(
            reverse("interactions:toggle-follow", args=[self.target.username])
        )
        self.assertEqual(followed.status_code, 201)
        self.assertTrue(followed.json()["following"])

        unfollowed = self.client.post(
            reverse("interactions:toggle-follow", args=[self.target.username])
        )
        self.assertEqual(unfollowed.status_code, 200)
        self.assertFalse(unfollowed.json()["following"])
        self.assertEqual(Follow.objects.count(), 0)

    def test_cannot_follow_yourself(self):
        self.client.force_login(self.fan)

        response = self.client.post(
            reverse("interactions:toggle-follow", args=[self.fan.username])
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Follow.objects.count(), 0)


class InteractionsAdminTests(TestCase):
    def test_all_interaction_models_are_registered_in_the_admin(self):
        for model in (Like, Save, Comment, Follow, PostView, PostCopy):
            with self.subTest(model=model):
                self.assertTrue(admin.site.is_registered(model))
