"""URL routing for the Terrasquid API v1."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ACLRuleViewSet,
    DestinationConfigViewSet,
    DestinationGroupViewSet,
    PortGroupViewSet,
    SourceACLViewSet,
    SourceGroupViewSet,
    StatusView,
)

router = DefaultRouter()
router.register(r"sources", SourceACLViewSet, basename="sourceacl")
router.register(r"source-groups", SourceGroupViewSet, basename="sourcegroup")
router.register(r"destinations", DestinationConfigViewSet, basename="destinationconfig")
router.register(r"destination-groups", DestinationGroupViewSet, basename="destinationgroup")
router.register(r"port-groups", PortGroupViewSet, basename="portgroup")
router.register(r"acl-rules", ACLRuleViewSet, basename="aclrule")

urlpatterns = [
    path("status/", StatusView.as_view(), name="status"),
    path("", include(router.urls)),
]
