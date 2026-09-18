from django.urls import path

from interactions import views

app_name = "interactions"

urlpatterns = [
    path("<int:post_id>/view/", views.record_view, name="record-view"),
    path("<int:post_id>/copy/", views.record_copy, name="record-copy"),
    path("<int:post_id>/like/", views.toggle_like, name="toggle-like"),
    path("<int:post_id>/save/", views.toggle_save, name="toggle-save"),
    path("<int:post_id>/comments/", views.list_comments, name="list-comments"),
    path("<int:post_id>/comments/create/", views.create_comment, name="create-comment"),
    path("comments/<int:comment_id>/delete/", views.delete_comment, name="delete-comment"),
    path("users/<str:username>/follow/", views.toggle_follow, name="toggle-follow"),
]
