"""
Esup-Pod - URL configuration for the layout app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from src.apps.layout.views import BlockConfigViewSet, BlockTypeViewSet

router = DefaultRouter()
router.register(r"blocks", BlockConfigViewSet, basename="blockconfig")
router.register(r"block-types", BlockTypeViewSet, basename="blocktype")

urlpatterns = [
    path("", include(router.urls)),
]
