from django.urls import path

from interactions import views

app_name = "interactions"

urlpatterns = [
    path("<int:post_id>/view/", views.record_view, name="record-view"),
    path("<int:post_id>/copy/", views.record_copy, name="record-copy"),
]
