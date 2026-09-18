from django.urls import path

from notifications import views

app_name = "notifications"

urlpatterns = [
    path("notifications/", views.notification_list, name="list"),
    path("notifications/read-all/", views.mark_all_read, name="read-all"),
    path("notifications/<int:notification_id>/read/", views.mark_read, name="read"),
]
