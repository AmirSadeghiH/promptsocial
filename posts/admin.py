from django.contrib import admin

from posts.models import Category, Post, Tag


class TagInline(admin.TabularInline):
    model = Post.tags.through
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "post_type", "category", "created_at")
    list_filter = ("post_type", "category", "created_at")
    search_fields = ("title", "description", "prompt", "ai_model", "author__username")
    autocomplete_fields = ("author", "category")
    filter_horizontal = ("tags",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "post_count", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Posts")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
