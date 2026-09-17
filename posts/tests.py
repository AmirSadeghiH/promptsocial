from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from interactions.models import Follow, PostCopy, PostView
from posts.models import Category, Post, Tag
from posts.services import get_following_feed, get_latest_feed, get_trending_feed


class FeedServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="feed-author",
            email="feed-author@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="Feed category", slug="feed-category")
        self.older_post = Post.objects.create(
            author=self.user,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Older prompt",
        )
        self.newer_post = Post.objects.create(
            author=self.user,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Newer prompt",
        )
        now = timezone.now()
        Post.objects.filter(pk=self.older_post.pk).update(created_at=now - timedelta(hours=2))
        Post.objects.filter(pk=self.newer_post.pk).update(created_at=now - timedelta(hours=1))

        self.viewer = get_user_model().objects.create_user(
            username="feed-viewer",
            email="feed-viewer@example.com",
            password="test-password",
        )
        followed_author = get_user_model().objects.create_user(
            username="followed-author",
            email="followed-author@example.com",
            password="test-password",
        )
        unfollowed_author = get_user_model().objects.create_user(
            username="unfollowed-author",
            email="unfollowed-author@example.com",
            password="test-password",
        )
        Follow.objects.create(follower=self.viewer, following=followed_author)
        self.followed_post = Post.objects.create(
            author=followed_author,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Followed author prompt",
        )
        self.unfollowed_post = Post.objects.create(
            author=unfollowed_author,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Unfollowed author prompt",
        )
        self.copied_post = Post.objects.create(
            author=followed_author,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Copied prompt",
        )
        self.viewed_post = Post.objects.create(
            author=unfollowed_author,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Viewed prompt",
        )
        PostCopy.objects.create(post=self.copied_post, user=self.viewer)
        for _ in range(5):
            PostView.objects.create(post=self.viewed_post, user=self.viewer)
        Post.objects.filter(pk=self.followed_post.pk).update(
            created_at=now - timedelta(hours=3),
        )
        Post.objects.filter(pk=self.unfollowed_post.pk).update(
            created_at=now - timedelta(hours=4),
        )
        Post.objects.filter(pk=self.copied_post.pk).update(
            created_at=now - timedelta(hours=5),
        )
        Post.objects.filter(pk=self.viewed_post.pk).update(
            created_at=now - timedelta(hours=6),
        )

    def test_latest_feed_returns_newest_post_first_with_a_next_cursor(self):
        page = get_latest_feed(page_size=1)

        self.assertEqual([item["id"] for item in page["results"]], [self.newer_post.id])
        self.assertIsNotNone(page["next_cursor"])

    def test_latest_cursor_returns_each_post_once(self):
        first_page = get_latest_feed(page_size=1)
        second_page = get_latest_feed(cursor=first_page["next_cursor"], page_size=1)

        self.assertEqual([item["id"] for item in second_page["results"]], [self.older_post.id])

    def test_following_feed_excludes_posts_by_unfollowed_authors(self):
        page = get_following_feed(self.viewer, page_size=20)

        result_ids = [item["id"] for item in page["results"]]
        self.assertIn(self.followed_post.id, result_ids)
        self.assertNotIn(self.unfollowed_post.id, result_ids)

    def test_trending_ranks_copy_above_equal_recent_view_activity(self):
        page = get_trending_feed(page_size=20)

        self.assertEqual(page["results"][0]["id"], self.copied_post.id)

    def test_trending_excludes_posts_older_than_thirty_days(self):
        old_post = Post.objects.create(
            author=self.user,
            category=self.older_post.category,
            post_type=Post.PostType.PROMPT,
            title="Old but popular prompt",
        )
        Post.objects.filter(pk=old_post.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )
        for _ in range(10):
            PostCopy.objects.create(post=old_post, user=self.viewer)

        page = get_trending_feed(page_size=20)

        self.assertNotIn(old_post.id, [item["id"] for item in page["results"]])


class FeedApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="api-feed-author",
            email="api-feed-author@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="API feeds", slug="api-feeds")
        self.post = Post.objects.create(
            author=self.user,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Feed API prompt",
        )

    def test_latest_endpoint_returns_json_page(self):
        response = self.client.get(reverse("posts:feed-latest"), {"page_size": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["id"], self.post.id)

    def test_anonymous_following_endpoint_returns_json_401(self):
        response = self.client.get(reverse("posts:feed-following"))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Authentication required."})

    def test_feed_endpoint_rejects_invalid_page_size(self):
        response = self.client.get(reverse("posts:feed-latest"), {"page_size": "0"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"error": "page_size must be an integer between 1 and 50."},
        )

    def test_feed_endpoint_rejects_an_invalid_cursor(self):
        response = self.client.get(reverse("posts:feed-latest"), {"cursor": "not-a-cursor"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid cursor."})

    def test_explore_endpoint_returns_discovery_sections(self):
        response = self.client.get(reverse("posts:explore"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {"latest", "trending", "popular_categories", "popular_creators"},
        )


class FeedQueryTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="query-author",
            email="query-author@example.com",
            password="test-password",
        )
        category = Category.objects.create(name="Query category", slug="query-category")
        tag = Tag.objects.create(
            name="efficient",
            slug="efficient",
        )
        for index in range(5):
            post = Post.objects.create(
                author=user,
                category=category,
                post_type=Post.PostType.PROMPT,
                title=f"Query prompt {index}",
            )
            post.tags.add(tag)

    def test_latest_feed_serializes_five_tagged_posts_in_two_queries(self):
        with CaptureQueriesContext(connection) as queries:
            page = get_latest_feed(page_size=5)

        self.assertEqual(len(page["results"]), 5)
        self.assertEqual(len(queries), 2)
