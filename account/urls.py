from django.urls import path

from account import views

app_name = "account"

urlpatterns = [
    path("auth/signup/", views.signup, name="signup"),
    path("auth/login/", views.api_login, name="login"),
    path("auth/logout/", views.api_logout, name="logout"),
    path("auth/me/", views.me, name="me"),
    path("me/update/", views.profile_update, name="profile-update"),
    path("me/saved/", views.saved_posts, name="saved-posts"),
    path("users/<str:username>/", views.profile_detail, name="profile-detail"),
]
