"""
Esup-Pod - BlockType ViewSet.

Exposes block types registered by the frontend at startup.
The /register/ endpoint is restricted to localhost only (no shared secret needed).
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from src.apps.layout.models import BlockType
from src.apps.layout.serializers import BlockTypeSerializer, BlockTypeRegisterSerializer
from src.apps.layout.utils import is_internal_request


@extend_schema_view(
    list=extend_schema(
        tags=["Layout Block Types"],
        summary="List all registered block types",
        description=(
            "Returns all block types that the frontend has registered. "
            "Use this in Django admin to know which block components are available."
        ),
        responses={200: BlockTypeSerializer(many=True)},
    ),
)
class BlockTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for BlockType.
    Block types are registered automatically by the frontend at startup via /register/.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = BlockTypeSerializer
    lookup_field = "frontend_id"
    queryset = BlockType.objects.all().order_by("name")

    @extend_schema(
        tags=["Layout Block Types"],
        summary="Register / update block types from the frontend",
        description=(
            "**Localhost only.** Called by the Next.js frontend at startup. "
            "Accepts a list of block manifests and upserts them via `update_or_create` "
            "on `frontend_id`. Idempotent — safe to call on every server restart."
        ),
        request=BlockTypeRegisterSerializer(many=True),
        responses={
            200: BlockTypeSerializer(many=True),
            403: {"description": "Forbidden — request must come from localhost."},
        },
    )
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        """
        Bulk upsert block types sent by the frontend manifest registry.
        Restricted to localhost requests only.
        """
        if not is_internal_request(request):
            return Response(
                {"detail": "This endpoint is only accessible from localhost."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = BlockTypeRegisterSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        results = []
        for item in serializer.validated_data:
            obj, created = BlockType.objects.update_or_create(
                frontend_id=item["frontend_id"],
                defaults={
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "fields_schema": item.get("fields_schema", {}),
                    "version": item.get("version", "1.0.0"),
                },
            )
            results.append(obj)

        out_serializer = BlockTypeSerializer(results, many=True)
        return Response(out_serializer.data, status=status.HTTP_200_OK)
