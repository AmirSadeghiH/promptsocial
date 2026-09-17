from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from interactions.models import PostCopy, PostView
from posts.models import Category, Post


class PostEngagementModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="event-user",
            email="event-user@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="Writing", slug="writing")
        self.post = Post.objects.create(
            author=self.user,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="A useful prompt",
        )

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
        category = Category.objects.create(name="Art", slug="art")
        self.post = Post.objects.create(
            author=self.user,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="An API prompt",
        )

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

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Authentication required."})
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


class InteractionsAdminTests(TestCase):
    def test_event_models_are_registered_in_the_admin(self):
        self.assertTrue(admin.site.is_registered(PostView))
        self.assertTrue(admin.site.is_registered(PostCopy))
