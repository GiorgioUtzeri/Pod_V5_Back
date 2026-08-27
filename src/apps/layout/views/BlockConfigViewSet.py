"""
Esup-Pod - BlockConfig ViewSet.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from src.apps.layout.models import BlockConfig, BlockType
from src.apps.layout.serializers import (
    BlockConfigSerializer,
    BlockConfigDefaultSerializer,
)
from src.apps.layout.conf import layout_settings
from src.apps.layout.utils import is_internal_request


@extend_schema_view(
    list=extend_schema(
        tags=["Layout Blocks"],
        summary="List all block configurations",
        description=(
            "Retrieve the list of all active block configurations defined by the administration. "
            "The frontend calls this endpoint on every page load to build its layout."
        ),
        responses={200: BlockConfigSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Layout Blocks"],
        summary="Retrieve a specific block configuration",
        responses={200: BlockConfigSerializer},
    ),
)
class BlockConfigViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to read and expose the layout configuration blocks.
    Block instances are managed in the Django admin by administrators.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = BlockConfigSerializer

    def get_queryset(self):
        """
        Return block configurations if enabled in settings, otherwise return an empty queryset.
        """
        if not layout_settings.use_layout_blocks:
            return BlockConfig.objects.none()
        return BlockConfig.objects.all().order_by("order", "id")

    @extend_schema(
        tags=["Layout Blocks"],
        summary="Sync default block configurations from the frontend",
        description=(
            "**Localhost only.** Called by the Next.js frontend at startup. "
            "Creates default `BlockConfig` instances using `get_or_create` on `admin_name`. "
            "Existing records are NEVER overwritten — admin customisations are preserved."
        ),
        request=BlockConfigDefaultSerializer(many=True),
        responses={
            200: BlockConfigSerializer(many=True),
            403: {"description": "Forbidden — request must come from localhost."},
        },
    )
    @action(detail=False, methods=["post"], url_path="sync-defaults")
    def sync_defaults(self, request):
        """
        Create default BlockConfig instances if they do not already exist.
        Safe to call on every server restart — uses get_or_create, never update.
        """
        if not is_internal_request(request):
            return Response(
                {"detail": "This endpoint is only accessible from localhost."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BlockConfigDefaultSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        for item in serializer.validated_data:
            # Resolve block_type FK if the BlockType has been registered
            block_type = BlockType.objects.filter(frontend_id=item["frontend_id"]).first()

            obj, created = BlockConfig.objects.get_or_create(
                admin_name=item["admin_name"],
                defaults={
                    "frontend_id": item["frontend_id"],
                    "block_type": block_type,
                    "order": item.get("order", 0),
                    "display_title": item.get("display_title"),
                    "item_limit": item.get("item_limit", 10),
                    "extra_config": item.get("extra_config", {}),
                    "is_active": True,
                },
            )
            # Always update FK link if block_type was registered later
            if block_type and obj.block_type != block_type:
                obj.block_type = block_type
                obj.save(update_fields=["block_type"])

            results.append(obj)

        out_serializer = BlockConfigSerializer(results, many=True)
        return Response(out_serializer.data, status=status.HTTP_200_OK)
