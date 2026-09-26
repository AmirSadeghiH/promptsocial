"""Tests for the AI image studio.

Nothing here touches the network: the provider is injected, so these tests
pin the behaviour that matters — quota windows, what a failure records, and
what the endpoint answers.
"""

import io
import json
import shutil
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from imagegen.client import GenerationError, ImageProvider, ProviderSettings
from imagegen.models import DEFAULT_BASE_URL, AIConfig, GeneratedImage
from imagegen.services import (
    MAX_PROMPT_LENGTH,
    PromptRejected,
    QuotaExceeded,
    check_quota,
    generate_image,
    prompt_library,
    quota_state,
)
from posts.models import Category, Post


def _png_bytes(size=32, color=(120, 80, 200)):
    buffer = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buffer, format="PNG")
    return buffer.getvalue()


class FakeProvider:
    """Stands in for the SDK call: returns bytes, or raises on demand."""

    def __init__(self, settings, *, payload=None, error=None):
        self.settings = settings
        self.payload = payload
        self.error = error
        self.calls = []

    def generate(self, prompt, size):
        self.calls.append({"prompt": prompt, "size": size})
        if self.error:
            raise self.error
        return self.payload if self.payload is not None else _png_bytes()


def _factory(*, payload=None, error=None):
    def build(settings):
        return FakeProvider(settings, payload=payload, error=error)

    return build


class MediaTestCase(TestCase):
    """Keeps generated files out of the real media root."""

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp(prefix="promptly-test-media-")
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)


class QuotaTests(MediaTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="studio-user",
            email="studio@example.com",
            password="test-password",
        )

    def _record(self, *, status=GeneratedImage.Status.READY, age=timedelta(0)):
        record = GeneratedImage.objects.create(
            user=self.user,
            prompt="A prompt",
            status=status,
            provider_model="test-model",
        )
        GeneratedImage.objects.filter(pk=record.pk).update(
            created_at=timezone.now() - age
        )
        return record

    def test_three_images_in_a_day_block_the_day_window(self):
        for _ in range(3):
            self._record()

        state = {entry["key"]: entry for entry in quota_state(self.user)}
        self.assertEqual(state["day"]["used"], 3)
        self.assertEqual(state["day"]["remaining"], 0)
        self.assertEqual(state["week"]["used"], 3)
        self.assertEqual(state["month"]["used"], 3)

        exceeded = check_quota(self.user)
        self.assertIsInstance(exceeded, QuotaExceeded)
        self.assertEqual(exceeded.window, "day")
        self.assertEqual(exceeded.limit, 3)

    def test_seven_images_in_a_week_block_the_week_window(self):
        for _ in range(7):
            self._record(age=timedelta(days=2))

        state = {entry["key"]: entry for entry in quota_state(self.user)}
        self.assertEqual(state["day"]["used"], 0)
        self.assertEqual(state["week"]["used"], 7)

        exceeded = check_quota(self.user)
        self.assertEqual(exceeded.window, "week")

    def test_fifteen_images_in_a_month_block_the_month_window(self):
        for _ in range(15):
            self._record(age=timedelta(days=10))

        state = {entry["key"]: entry for entry in quota_state(self.user)}
        self.assertEqual(state["week"]["used"], 0)
        self.assertEqual(state["month"]["used"], 15)
        self.assertEqual(check_quota(self.user).window, "month")

    def test_attempts_older_than_a_window_stop_counting(self):
        self._record(age=timedelta(hours=25), status=GeneratedImage.Status.READY)

        state = {entry["key"]: entry for entry in quota_state(self.user)}
        self.assertEqual(state["day"]["used"], 0)
        self.assertEqual(state["week"]["used"], 1)
        self.assertIsNone(check_quota(self.user))

    def test_failed_attempts_do_not_burn_the_allowance(self):
        for _ in range(5):
            self._record(status=GeneratedImage.Status.FAILED)

        state = {entry["key"]: entry for entry in quota_state(self.user)}
        self.assertEqual(state["day"]["used"], 0)
        self.assertIsNone(check_quota(self.user))

    def test_reset_seconds_point_at_the_oldest_attempt(self):
        self._record(age=timedelta(hours=23))
        self._record()

        day = quota_state(self.user)[0]
        self.assertLessEqual(day["reset_in_seconds"], 3600)
        self.assertGreater(day["reset_in_seconds"], 0)

    def test_quota_state_is_empty_for_anonymous_users(self):
        self.assertEqual(quota_state(None), [])


class GenerationTests(MediaTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="generator",
            email="generator@example.com",
            password="test-password",
        )
        self.config = AIConfig.objects.create(
            api_key="sk-test",
            model="gapgpt/z-image",
            base_url="https://api.gapgpt.app/v1",
            image_size="1024x1024",
        )

    def test_successful_generation_stores_the_image(self):
        record = generate_image(
            self.user, "  A sunset over mountains  ", provider_factory=_factory()
        )

        self.assertEqual(record.status, GeneratedImage.Status.READY)
        self.assertEqual(record.prompt, "A sunset over mountains")
        self.assertTrue(record.image.name.endswith(".png"))
        self.assertTrue(record.image.storage.exists(record.image.name))
        self.assertIsNotNone(record.finished_at)
        self.assertEqual(record.provider_model, "gapgpt/z-image")

    def test_generation_uses_the_configured_size_and_model(self):
        captured = {}

        def build(settings):
            provider = FakeProvider(settings)
            captured["settings"] = settings
            return provider

        generate_image(self.user, "A mountain", provider_factory=build)
        self.assertEqual(captured["settings"].model, "gapgpt/z-image")
        self.assertEqual(captured["settings"].base_url, "https://api.gapgpt.app/v1")

    def test_provider_failure_is_recorded_and_reraised(self):
        with self.assertRaises(GenerationError):
            generate_image(
                self.user,
                "A mountain",
                provider_factory=_factory(error=GenerationError("The provider is down.")),
            )

        record = GeneratedImage.objects.get()
        self.assertEqual(record.status, GeneratedImage.Status.FAILED)
        self.assertEqual(record.error, "The provider is down.")
        self.assertFalse(record.image)
        self.assertIsNone(check_quota(self.user))

    def test_unexpected_provider_bug_becomes_a_generation_error(self):
        with self.assertRaises(GenerationError):
            generate_image(
                self.user,
                "A mountain",
                provider_factory=_factory(error=RuntimeError("boom")),
            )

        record = GeneratedImage.objects.get()
        self.assertEqual(record.status, GeneratedImage.Status.FAILED)
        self.assertTrue(record.error)

    def test_non_image_payload_is_rejected(self):
        with self.assertRaises(GenerationError):
            generate_image(
                self.user,
                "A mountain",
                provider_factory=_factory(payload=b"<html>not an image</html>"),
            )
        self.assertEqual(GeneratedImage.objects.get().status, GeneratedImage.Status.FAILED)

    def test_empty_prompt_is_rejected(self):
        with self.assertRaises(PromptRejected):
            generate_image(self.user, "   ", provider_factory=_factory())
        self.assertFalse(GeneratedImage.objects.exists())

    def test_overlong_prompt_is_rejected(self):
        with self.assertRaises(PromptRejected):
            generate_image(
                self.user, "x" * (MAX_PROMPT_LENGTH + 1), provider_factory=_factory()
            )

    def test_quota_is_enforced_before_calling_the_provider(self):
        provider = FakeProvider(ProviderSettings("https://api.example/v1", "sk", "m"))

        def build(settings):
            called.append(True)
            return provider

        called = []
        for _ in range(3):
            generate_image(self.user, "A mountain", provider_factory=_factory())

        with self.assertRaises(QuotaExceeded):
            generate_image(self.user, "A mountain", provider_factory=build)
        self.assertEqual(called, [])
        self.assertEqual(GeneratedImage.objects.count(), 3)

    def test_generation_is_refused_without_an_api_key(self):
        AIConfig.objects.update(api_key="", is_enabled=True)

        with self.assertRaises(GenerationError):
            generate_image(self.user, "A mountain", provider_factory=_factory())
        self.assertFalse(GeneratedImage.objects.exists())

    def test_generation_is_refused_when_disabled(self):
        AIConfig.objects.update(is_enabled=False)

        with self.assertRaises(GenerationError):
            generate_image(self.user, "A mountain", provider_factory=_factory())


class AIConfigTests(TestCase):
    def test_load_returns_defaults_without_a_row(self):
        config = AIConfig.load()
        self.assertIsNone(config.pk)
        self.assertEqual(config.base_url, DEFAULT_BASE_URL)
        self.assertEqual(config.model, "gapgpt/z-image")
        self.assertFalse(config.is_ready)

    def test_is_ready_requires_a_key_and_the_switch(self):
        config = AIConfig.objects.create(api_key="sk-test")
        self.assertTrue(config.is_ready)

        config.is_enabled = False
        self.assertFalse(config.is_ready)


class ProviderSettingsTests(TestCase):
    def test_incomplete_settings_are_refused(self):
        settings = ProviderSettings(base_url="", api_key="", model="")
        self.assertFalse(settings.is_complete)
        with self.assertRaises(GenerationError):
            ImageProvider(settings).generate("A mountain", "1024x1024")

    def test_missing_credentials_never_reach_the_network(self):
        settings = ProviderSettings("https://api.example/v1", "", "gapgpt/z-image")
        with self.assertRaises(GenerationError):
            ImageProvider(settings).generate("A mountain", "1024x1024")


class PromptLibraryTests(MediaTestCase):
    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username="librarian",
            email="librarian@example.com",
            password="test-password",
        )
        self.category = Category.objects.create(name="Art", slug="art")

    def _post(self, *, prompt, title="A prompt", image=True, post_type=Post.PostType.IMAGE):
        post = Post.objects.create(
            author=self.author,
            category=self.category,
            post_type=post_type,
            title=title,
            prompt=prompt,
        )
        if image:
            post.image.save(
                f"{title}.png", ContentFile(_png_bytes()), save=True
            )
        return post

    def test_library_lists_prompts_with_their_output(self):
        self._post(prompt="A cathedral made of glass")
        self._post(prompt="An astronaut in a garden", post_type=Post.PostType.PROMPT, image=False)

        library = prompt_library()
        prompts = {item["prompt"] for item in library}
        self.assertEqual(prompts, {"A cathedral made of glass", "An astronaut in a garden"})
        with_image = next(item for item in library if item["prompt"] == "A cathedral made of glass")
        self.assertTrue(with_image["image"].startswith("/media/"))
        self.assertEqual(with_image["author"], "librarian")

    def test_image_posts_without_an_upload_are_skipped(self):
        self._post(prompt="No output yet", image=False)
        self.assertEqual(prompt_library(), [])

    def test_empty_prompts_are_skipped(self):
        self._post(prompt="", image=True)
        self.assertEqual(prompt_library(), [])

    def test_duplicate_prompts_collapse(self):
        self._post(prompt="Same prompt", title="First")
        self._post(prompt="Same prompt", title="Second")
        self.assertEqual(len(prompt_library()), 1)


class StudioApiTests(MediaTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="api-user",
            email="api-user@example.com",
            password="test-password",
        )
        self.url = reverse("imagegen:generate")
        self.config = AIConfig.objects.create(api_key="sk-test", model="gapgpt/z-image")

    def _post_json(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_anonymous_request_gets_a_401_json_response(self):
        response = self._post_json({"prompt": "A mountain"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Authentication required.")

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_successful_generation_returns_the_image_and_quota(self):
        self.client.force_login(self.user)
        with patch("imagegen.services.ImageProvider", _factory()):
            response = self._post_json({"prompt": "A mountain at dawn"})

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["generation"]["prompt"], "A mountain at dawn")
        self.assertIn("/media/generated_images/", body["generation"]["image"])
        quota = {entry["key"]: entry for entry in body["quota"]}
        self.assertEqual(quota["day"]["used"], 1)
        self.assertEqual(quota["day"]["remaining"], 2)

    def test_empty_prompt_is_a_400(self):
        self.client.force_login(self.user)
        with patch("imagegen.services.ImageProvider", _factory()):
            response = self._post_json({"prompt": "   "})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "invalid_prompt")

    def test_invalid_json_is_a_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, data="{", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "bad_request")

    def test_exhausted_quota_is_a_429_with_the_reset_time(self):
        self.client.force_login(self.user)
        for _ in range(3):
            GeneratedImage.objects.create(
                user=self.user, prompt="p", status=GeneratedImage.Status.READY
            )

        with patch("imagegen.services.ImageProvider", _factory()):
            response = self._post_json({"prompt": "A mountain"})

        self.assertEqual(response.status_code, 429)
        body = response.json()
        self.assertEqual(body["error_code"], "quota_exceeded")
        self.assertEqual(body["window"], "day")
        self.assertEqual(body["limit"], 3)
        self.assertIn("retry_after_seconds", body)
        self.assertEqual(len(body["quota"]), 3)

    def test_provider_failure_is_a_502_and_is_recorded(self):
        self.client.force_login(self.user)
        provider = _factory(error=GenerationError("The provider is down."))
        with patch("imagegen.services.ImageProvider", provider):
            response = self._post_json({"prompt": "A mountain"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error_code"], "provider_error")
        self.assertEqual(GeneratedImage.objects.get().status, GeneratedImage.Status.FAILED)

    def test_generation_is_refused_when_the_provider_is_unconfigured(self):
        AIConfig.objects.update(api_key="")
        self.client.force_login(self.user)
        response = self._post_json({"prompt": "A mountain"})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error_code"], "provider_error")

    def test_source_post_is_linked_to_the_generation(self):
        category = Category.objects.create(name="Art", slug="art")
        source = Post.objects.create(
            author=self.user,
            category=category,
            post_type=Post.PostType.PROMPT,
            title="Source",
            prompt="A cathedral made of glass",
        )
        self.client.force_login(self.user)
        with patch("imagegen.services.ImageProvider", _factory()):
            response = self._post_json(
                {"prompt": "A cathedral made of glass", "source_post_id": source.pk}
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["generation"]["source_post_id"], source.pk)


class StudioPageTests(MediaTestCase):
    def setUp(self):
        self.url = reverse("web:studio")
        self.author = get_user_model().objects.create_user(
            username="shelf-owner",
            email="shelf@example.com",
            password="test-password",
        )
        self.category = Category.objects.create(name="Art", slug="art")

    def test_page_renders_for_anonymous_visitors(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Log in to generate")

    def test_page_seeds_the_studio_data_and_quota(self):
        GeneratedImage.objects.create(
            user=self.author, prompt="A latent idea", status=GeneratedImage.Status.READY
        )
        self.client.force_login(self.author)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "studio-data")
        self.assertContains(response, "A latent idea")
        data = response.context["studio_data"]
        self.assertEqual(data["quota"][0]["used"], 1)
        self.assertEqual(len(data["generations"]), 1)

    def test_library_shows_a_copyable_prompt(self):
        post = Post.objects.create(
            author=self.author,
            category=self.category,
            post_type=Post.PostType.PROMPT,
            title="Glass cathedral",
            prompt="A cathedral made of glass, refracted light",
        )
        response = self.client.get(self.url)
        self.assertContains(response, "A cathedral made of glass, refracted light")
        self.assertContains(response, f'data-post-id="{post.pk}"')
