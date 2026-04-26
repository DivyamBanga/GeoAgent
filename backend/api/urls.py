from django.urls import path
from . import views

urlpatterns = [
    path("analyze/", views.analyze, name="analyze"),
    path("analyze/stream/", views.analyze_stream, name="analyze_stream"),
    path("health/", views.health, name="health"),
]
