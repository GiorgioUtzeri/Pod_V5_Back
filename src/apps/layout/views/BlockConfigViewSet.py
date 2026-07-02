"""
Esup-Pod - BlockConfig ViewSet.
"""

from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema
from src.apps.layout.models import BlockConfig
from src.apps.layout.serializers import BlockConfigSerializer
from src.apps.layout.conf import layout_settings


@extend_schema(
    tags=["Layout Blocks"],
    description="Endpoints to manage the visual layout blocks configuration used by the frontend.",
)
class BlockConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A simple ViewSet for viewing layout block configurations.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = BlockConfigSerializer
    lookup_field = "frontend_id"

    def get_queryset(self):
        """
        Return block configurations if enabled in settings, otherwise return none.
        """
        if not layout_settings.use_layout_blocks:
            return BlockConfig.objects.none()
        return BlockConfig.objects.all().order_by("frontend_id")

    @extend_schema(
        summary="List all block configurations",
        description=(
            "Retrieve the list of all block configurations defined by the administration. "
            "The frontend should call this endpoint upon initialization to configure its layout components."
        ),
        responses={200: BlockConfigSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """List blocks."""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a specific block configuration",
        description="Retrieve the personalization settings for a specific block using its `frontend_id`.",
        responses={200: BlockConfigSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        """Retrieve block by frontend_id."""
        return super().retrieve(request, *args, **kwargs)
