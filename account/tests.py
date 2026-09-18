from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from interactions.models import Follow, Save
from posts.models import Category, Post


def _make_post(author, title):
    category, _ = Category.objects.get_or_create(name="Writing", slug="writing")
    return Post.objects.create(
        author=author,
        category=category,
        post_type=Post.PostType.PROMPT,
        title=title,
    )


class AuthApiTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("account:signup"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "super-secret-123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            get_user_model().objects.filter(username="newuser").exists()
        )
        me = self.client.get(reverse("account:me"))
        self.assertEqual(me.json()["user"]["username"], "newuser")

    def test_signup_rejects_duplicate_username(self):
        get_user_model().objects.create_user(
            username="taken",
            email="taken@example.com",
            password="test-password",
        )

        response = self.client.post(
            reverse("account:signup"),
            {
                "username": "TAKEN",
                "email": "other@example.com",
                "password": "super-secret-123",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["errors"])

    def test_login_with_username_or_email(self):
        get_user_model().objects.create_user(
            username="loginuser",
            email="loginuser@example.com",
            password="super-secret-123",
        )

        by_username = self.client.post(
            reverse("account:login"),
            {"username": "loginuser", "password": "super-secret-123"},
            content_type="application/json",
        )
        self.assertEqual(by_username.status_code, 200)

        self.client.post(reverse("account:logout"))
        by_email = self.client.post(
            reverse("account:login"),
            {"username": "loginuser@example.com", "password": "super-secret-123"},
            content_type="application/json",
        )
        self.assertEqual(by_email.status_code, 200)

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(
            reverse("account:login"),
            {"username": "ghost", "password": "wrong"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("account:me"))

        self.assertEqual(response.status_code, 401)


class ProfileApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="profileuser",
            email="profileuser@example.com",
            password="test-password",
            display_name="Profile User",
        )
        self.post = _make_post(self.user, "My showcased prompt")

    def test_profile_detail_includes_posts_and_counts(self):
        response = self.client.get(reverse("account:profile-detail", args=["profileuser"]))

        self.assertEqual(response.status_code, 200)
        data = response.json()["user"]
        self.assertEqual(data["username"], "profileuser")
        self.assertEqual(data["post_count"], 1)
        self.assertEqual(data["posts"][0]["title"], "My showcased prompt")

    def test_profile_update_requires_login(self):
        response = self.client.patch(
            reverse("account:profile-update"),
            {"biography": "nope"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 302)

    def test_owner_can_update_profile(self):
        self.client.force_login(self.user)

        response = self.client.patch(
            reverse("account:profile-update"),
            {"biography": "Prompt collector.", "display_name": "Pro"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.biography, "Prompt collector.")


class SavedPostsApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="saver",
            email="saver@example.com",
            password="test-password",
        )
        self.author = get_user_model().objects.create_user(
            username="saver-author",
            email="saver-author@example.com",
            password="test-password",
        )
        self.post_a = _make_post(self.author, "Saved first")
        self.post_b = _make_post(self.author, "Saved second")

    def test_saved_posts_requires_login(self):
        response = self.client.get(reverse("account:saved-posts"))

        self.assertEqual(response.status_code, 302)

    def test_saved_posts_returns_saved_posts_newest_save_first(self):
        Save.objects.create(user=self.user, post=self.post_a)
        Save.objects.create(user=self.user, post=self.post_b)
        self.client.force_login(self.user)

        response = self.client.get(reverse("account:saved-posts"))

        self.assertEqual(response.status_code, 200)
        titles = [p["title"] for p in response.json()["results"]]
        self.assertEqual(titles, ["Saved second", "Saved first"])


class FollowCountsTests(TestCase):
    def test_profile_shows_follower_and_following_counts(self):
        alice = get_user_model().objects.create_user(
            username="alice", email="alice@example.com", password="test-password",
        )
        bob = get_user_model().objects.create_user(
            username="bob", email="bob@example.com", password="test-password",
        )
        Follow.objects.create(follower=bob, following=alice)

        response = self.client.get(reverse("account:profile-detail", args=["alice"]))
        data = response.json()["user"]

        self.assertEqual(data["follower_count"], 1)
        self.assertEqual(data["following_count"], 0)
