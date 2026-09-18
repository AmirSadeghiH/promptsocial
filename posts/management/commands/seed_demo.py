"""Seed the database with demo content: users, categories, posts and interactions.

Usage: python manage.py seed_demo
"""
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from interactions.models import Comment, Follow, Like, Save
from posts.models import Category, Post, Tag

CATEGORIES = [
    ("Writing", "Story, copy and creative writing prompts"),
    ("Image Generation", "Prompts for Midjourney, DALL·E, Stable Diffusion"),
    ("Video", "Prompts for Sora, Runway and friends"),
    ("Coding", "Prompts that help you build software"),
    ("Marketing", "Ads, landing pages and growth prompts"),
    ("Productivity", "Prompts for planning and personal ops"),
]

AI_MODELS = ["GPT-5", "Claude", "Midjourney", "DALL·E 3", "Sora", "Stable Diffusion", "Gemini"]

POST_TITLES = [
    "Cinematic portrait with dramatic lighting",
    "Sci-fi city at golden hour",
    "Story generator with a twist ending",
    "One-line landing page copywriter",
    "Refactor legacy code in safe steps",
    "Minimal logo design brief",
    "Isometric cozy room illustration",
    "Email sequence that actually converts",
    "Weekly planner powered by AI",
    "Watercolor wildlife scene",
    "Cyberpunk street photography look",
    "Explain code like a senior mentor",
    "Viral hook generator for shorts",
    "Dreamy pastel landscape",
    "Bug hunter: find the edge cases",
    "Product photo on marble background",
    "Fantasy map generator",
    "Cold email that gets replies",
    "Retro 80s synthwave poster",
    "Interview prep simulator",
]

PROMPT_EXCERPTS = [
    "Create a scene where {subject} is lit by a single warm light source, shot on 85mm, shallow depth of field, subtle film grain...",
    "Write a {length} story about {subject} that ends with an unexpected but inevitable twist. Keep the tone literary...",
    "Design {subject} using flat vectors, a limited palette of 3 colors, and generous negative space...",
    "You are a senior engineer. Review the following code and suggest the smallest safe refactor...",
]


class Command(BaseCommand):
    help = "Seed the database with demo users, categories, posts and interactions."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo data first")

    def handle(self, *args, **options):
        User = get_user_model()
        rng = random.Random(42)

        if options["flush"]:
            Post.objects.all().delete()
            Like.objects.all().delete()
            Save.objects.all().delete()
            Comment.objects.all().delete()
            Follow.objects.all().delete()
            User.objects.filter(username__startswith="demo_").delete()
            self.stdout.write("Cleared existing demo data.")

        categories = []
        for name, description in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "description": description}
            )
            categories.append(category)

        tags = []
        for name in ["midjourney", "gpt", "storytelling", "ux", "seo", "shorts", "photo", "code"]:
            tag, _ = Tag.objects.get_or_create(name=name, slug=slugify(name))
            tags.append(tag)

        users = []
        for i in range(8):
            username = f"demo_{['nova', 'atlas', 'mira', 'echo', 'pixel', 'quill', 'vivid', 'orbit'][i]}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "display_name": username.replace("demo_", "").capitalize(),
                    "biography": "Prompt artist exploring what AI can do.",
                    "is_verified": i < 2,
                },
            )
            if created:
                user.set_password("demo-password-123")
                user.save()
            users.append(user)

        # Everyone follows the first two users (the "verified" ones)
        for follower in users[2:]:
            for target in users[:2]:
                Follow.objects.get_or_create(follower=follower, following=target)

        created_posts = []
        for index, title in enumerate(POST_TITLES):
            author = rng.choice(users)
            category = rng.choice(categories)
            subject = rng.choice(["a lone traveler", "an ancient library", "a bioluminescent forest", "a quiet café"])
            prompt = rng.choice(PROMPT_EXCERPTS).format(subject=subject, length="flash-fiction")
            post, created = Post.objects.get_or_create(
                title=title,
                defaults={
                    "author": author,
                    "category": category,
                    "post_type": rng.choices(
                        [Post.PostType.PROMPT, Post.PostType.IMAGE, Post.PostType.VIDEO],
                        weights=[6, 3, 1],
                    )[0],
                    "prompt": prompt,
                    "description": f"Demo post #{index + 1} — {category.name.lower()} prompt.",
                    "ai_model": rng.choice(AI_MODELS),
                },
            )
            if created:
                post.tags.set(rng.sample(tags, k=rng.randint(1, 3)))
                # Spread created_at over the last 30 days
                Post.objects.filter(pk=post.pk).update(
                    created_at=timezone.now() - timezone.timedelta(days=rng.uniform(0, 29), hours=rng.randint(0, 23))
                )
            created_posts.append(post)

        for post in created_posts:
            for user in rng.sample(users, k=rng.randint(2, len(users))):
                Like.objects.get_or_create(user=user, post=post)
            if rng.random() < 0.6:
                Save.objects.get_or_create(user=rng.choice(users), post=post)
            for _ in range(rng.randint(0, 3)):
                commenter = rng.choice(users)
                Comment.objects.get_or_create(
                    post=post,
                    user=commenter,
                    defaults={"content": rng.choice([
                        "Tried this — the results are stunning.",
                        "Saved for later, thanks!",
                        "Works even better with a wider lens.",
                        "Great prompt, simple and effective.",
                    ])},
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(users)} users, {len(categories)} categories, "
                f"{len(created_posts)} posts, {Like.objects.count()} likes, "
                f"{Comment.objects.count()} comments."
            )
        )
