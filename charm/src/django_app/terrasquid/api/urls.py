"""URL routing for the Terrasquid API v1."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ACLRuleViewSet,
    DestinationConfigViewSet,
    SourceACLViewSet,
    StatusView,
)

router = DefaultRouter()
router.register(r"sources", SourceACLViewSet, basename="sourceacl")
router.register(r"destinations", DestinationConfigViewSet, basename="destinationconfig")
router.register(r"acl-rules", ACLRuleViewSet, basename="aclrule")

urlpatterns = [
    path("status/", StatusView.as_view(), name="status"),
    path("", include(router.urls)),
]
