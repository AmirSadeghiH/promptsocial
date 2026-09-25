from django.urls import path

from posts import views

app_name = "posts"

urlpatterns = [
    path("feed/latest/", views.feed_latest, name="feed-latest"),
    path("feed/following/", views.feed_following, name="feed-following"),
    path("feed/trending/", views.feed_trending, name="feed-trending"),
    path("feed/recommended/", views.feed_recommended, name="feed-recommended"),
    path("explore/", views.explore, name="explore"),
    path("search/", views.search, name="search"),
    path("categories/", views.category_list, name="categories"),
    path("categories/<str:slug>/", views.category_posts, name="category-posts"),
    path("tags/", views.tag_list, name="tags"),
    path("create/", views.post_create, name="post-create"),
    path("<int:pk>/", views.post_detail, name="post-detail"),
    path("<int:pk>/update/", views.post_update, name="post-update"),
    path("<int:pk>/delete/", views.post_delete, name="post-delete"),
]
