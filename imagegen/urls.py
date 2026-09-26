from django.urls import path

from imagegen import views

app_name = "imagegen"

urlpatterns = [
    path("ai/generate/", views.api_generate, name="generate"),
]
