"""URL configuration for the Terrasquid project."""

import os

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("terrasquid.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

# Django admin interface is disabled by default for security (known brute-force target).
# Enable only if DJANGO_ADMIN_ENABLED env var is explicitly set to "true".
if os.environ.get("DJANGO_ADMIN_ENABLED", "false").lower() == "true":
    urlpatterns.insert(0, path("admin/", admin.site.urls))
