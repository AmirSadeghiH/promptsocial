from django.contrib import admin

from interactions.models import PostCopy, PostView


@admin.register(PostView)
class PostViewAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    list_select_related = ("post", "user")
    ordering = ("-created_at",)


@admin.register(PostCopy)
class PostCopyAdmin(admin.ModelAdmin):
    list_display = ("post", "user", "created_at")
    list_select_related = ("post", "user")
    ordering = ("-created_at",)
