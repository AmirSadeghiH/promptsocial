from django.urls import path

from posts import views

app_name = "posts"

urlpatterns = [
    path("feed/latest/", views.feed_latest, name="feed-latest"),
    path("feed/following/", views.feed_following, name="feed-following"),
    path("feed/trending/", views.feed_trending, name="feed-trending"),
    path("explore/", views.explore, name="explore"),
]
