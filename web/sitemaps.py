"""XML sitemaps for every publicly indexable surface of the site.

Registered under `/sitemap.xml` in ``web.urls``. Django paginates and caches
each sitemap and only the columns a sitemap needs are loaded, so this stays
cheap even as the post table grows.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from account.models import CustomUser
from posts.models import Category, Post


class PostSitemap(Sitemap):
    """The site's primary content: every published prompt post."""

    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return Post.objects.only("id", "updated_at").order_by("-created_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("web:post-detail", args=[obj.pk])


class ProfileSitemap(Sitemap):
    """Public creator profiles."""

    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return (
            CustomUser.objects.filter(is_active=True)
            .only("id", "username", "updated_at")
            .order_by("username")
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("web:profile", args=[obj.username])


class CategorySitemap(Sitemap):
    """Category hubs."""

    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return Category.objects.only("id", "slug", "created_at").order_by("slug")

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return reverse("web:category", args=[obj.slug])


class StaticViewSitemap(Sitemap):
    """The handful of non-parameterised entry points worth crawling."""

    priority = 0.8
    changefreq = "daily"
    # (url name, positional args) — `web:feed` requires its variant.
    _entries = (
        ("home", ()),
        ("explore", ()),
        ("feed", ("trending",)),
        ("feed", ("latest",)),
    )

    def items(self):
        return self._entries

    def location(self, item):
        name, args = item
        return reverse(f"web:{name}", args=args)


SITEMAPS = {
    "posts": PostSitemap,
    "profiles": ProfileSitemap,
    "categories": CategorySitemap,
    "static": StaticViewSitemap,
}
