from django.urls import path
from .views import certificate_view

urlpatterns = [
    path("<uuid:uuid>/", certificate_view, name="certificate_view"),
]