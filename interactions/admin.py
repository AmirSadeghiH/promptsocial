from django.contrib import admin

from interactions.models import Comment, Follow, Like, PostCopy, PostView, Save


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


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    list_select_related = ("user", "post")
    search_fields = ("user__username", "post__title")
    ordering = ("-created_at",)


@admin.register(Save)
class SaveAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    list_select_related = ("user", "post")
    search_fields = ("user__username", "post__title")
    ordering = ("-created_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "short_content", "created_at")
    list_select_related = ("user", "post")
    search_fields = ("user__username", "post__title", "content")
    ordering = ("-created_at",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:60]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    list_select_related = ("follower", "following")
    search_fields = ("follower__username", "following__username")
    ordering = ("-created_at",)
