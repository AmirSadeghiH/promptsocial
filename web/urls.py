from django.contrib.sitemaps.views import sitemap
from django.urls import path

from web import views
from web.sitemaps import SITEMAPS

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("explore/", views.explore_page, name="explore"),
    path("search/", views.search_page, name="search"),
    path("create/", views.create_post_page, name="create"),
    path("saved/", views.saved_page, name="saved"),
    path("notifications/", views.notifications_page, name="notifications"),
    path("profile/<str:username>/", views.profile_page, name="profile"),
    path("settings/profile/", views.profile_edit_page, name="profile-edit"),
    path("category/<str:slug>/", views.category_page, name="category"),
    path("post/<int:pk>/", views.post_detail_page, name="post-detail"),
    path("feed/<str:feed>/", views.feed_page, name="feed"),
    path("offline/", views.offline_page, name="offline"),
    # --- SEO plumbing ---
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
]
