"""Tests for media upload validation and profile edit APIs."""
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from posts.validation import validate_upload_file
from PIL import Image


def _png_bytes(size=64, color=(120, 80, 200)):
    buffer = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(name, content, content_type):
    return SimpleUploadedFile(name, content, content_type=content_type)


class UploadValidationTests(TestCase):
    def test_accepts_real_png(self):
        f = _upload("avatar.png", _png_bytes(), "image/png")
        validate_upload_file(f, "image")  # should not raise

    def test_accepts_real_jpeg(self):
        buffer = io.BytesIO()
        Image.new("RGB", (32, 32), (10, 10, 10)).save(buffer, format="JPEG")
        f = _upload("avatar.jpg", buffer.getvalue(), "image/jpeg")
        validate_upload_file(f, "image")  # should not raise

    def test_rejects_disallowed_extension(self):
        f = _upload("shell.svg", b"<svg onload=alert(1)>", "image/svg+xml")
        with self.assertRaises(Exception):
            validate_upload_file(f, "image")

    def test_rejects_executable_disguised_as_png(self):
        f = _upload("malware.png", b"MZ\x90\x00" + b"\x00" * 200, "image/png")
        with self.assertRaises(Exception):
            validate_upload_file(f, "image")

    def test_rejects_gif_renamed_to_png(self):
        gif = b"GIF89a" + b"\x00" * 64
        f = _upload("fake.png", gif, "image/png")
        with self.assertRaises(Exception):
            validate_upload_file(f, "image")

    def test_rejects_oversized_image(self):
        class BigFile:
            name = "big.png"
            size = 11 * 1024 * 1024
            content_type = "image/png"
            def read(self, n=-1):
                return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
            def seek(self, *a):
                pass
        with self.assertRaises(Exception):
            validate_upload_file(BigFile(), "image")

    def test_video_extension_check(self):
        f = _upload("clip.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64, "video/mp4")
        validate_upload_file(f, "video")  # should not raise

        bad = _upload("clip.mp4", b"definitely not a video" * 10, "video/mp4")
        with self.assertRaises(Exception):
            validate_upload_file(bad, "video")


class PostCreateMediaMatchingTests(TestCase):
    """post_create must enforce that media matches the declared post type."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="poster", email="poster@example.com", password="test-password"
        )
        self.client.force_login(self.user)
        from posts.models import Category
        self.category = Category.objects.create(name="Testing", slug="testing")
        self.url = "/api/posts/create/"

    def _base(self, post_type):
        return {
            "title": "A post",
            "post_type": post_type,
            "category_id": str(self.category.id),
            "prompt": "p" * 10,
        }

    def test_image_post_requires_image(self):
        response = self.client.post(self.url, self._base("image"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("media", response.json()["errors"])

    def test_prompt_post_rejects_media(self):
        data = self._base("prompt")
        data["video"] = _upload("clip.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64, "video/mp4")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)

    def test_video_post_rejects_image_field(self):
        data = self._base("video")
        data["image"] = _upload("pic.png", _png_bytes(), "image/png")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 400)

    def test_video_post_accepts_only_video(self):
        data = self._base("video")
        data["video"] = _upload("clip.mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00" + b"\x00" * 64, "video/mp4")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 201, response.content)

    def test_prompt_post_without_media_succeeds(self):
        response = self.client.post(self.url, self._base("prompt"))
        self.assertEqual(response.status_code, 201, response.content)


class ProfileEditApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="editor",
            email="editor@example.com",
            password="original-pass-123",
            display_name="Editor",
        )
        self.client.force_login(self.user)

    def test_multipart_profile_update_fields_and_avatar(self):
        response = self.client.post(
            reverse("account:profile-multipart"),
            {
                "username": "editor_renamed",
                "display_name": "Edited Name",
                "biography": "I prompt, therefore I am.",
                "profile_picture": _upload(
                    "avatar.png", _png_bytes(), "image/png"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "editor_renamed")
        self.assertEqual(self.user.display_name, "Edited Name")
        self.assertEqual(self.user.biography, "I prompt, therefore I am.")
        self.assertTrue(self.user.profile_picture)

    def test_avatar_upload_rejects_disguised_file(self):
        response = self.client.post(
            reverse("account:profile-multipart"),
            {
                "profile_picture": _upload(
                    "evil.png", b"MZ\x90\x00" + b"\x00" * 200, "image/png"
                ),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("profile_picture", response.json()["errors"])
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_picture)

    def test_duplicate_username_rejected(self):
        get_user_model().objects.create_user(
            username="occupied", email="occupied@example.com", password="test-password"
        )
        response = self.client.post(
            reverse("account:profile-multipart"), {"username": "OCCUPIED"}
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_flow(self):
        response = self.client.post(
            reverse("account:change-password"),
            {"current_password": "wrong-current", "new_password": "brand-new-pass-99"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

        ok = self.client.post(
            reverse("account:change-password"),
            {"current_password": "original-pass-123", "new_password": "brand-new-pass-99"},
            content_type="application/json",
        )
        self.assertEqual(ok.status_code, 200)

        # Session must survive the password change.
        me = self.client.get(reverse("account:me"))
        self.assertEqual(me.status_code, 200)

    def test_change_password_rejects_weak(self):
        response = self.client.post(
            reverse("account:change-password"),
            {"current_password": "original-pass-123", "new_password": "12345678"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
