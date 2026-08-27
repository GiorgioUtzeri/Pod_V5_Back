"""
Esup-Pod - BlockConfig serializers.
"""

from rest_framework import serializers
from src.apps.layout.models import BlockConfig


class BlockConfigSerializer(serializers.ModelSerializer):
    """Serializer for BlockConfig."""

    class Meta:
        """Meta options."""

        model = BlockConfig
        fields = [
            "id",
            "frontend_id",
            "order",
            "is_active",
            "display_title",
            "subtitle_or_text",
            "item_limit",
            "background_color",
            "text_color",
            "extra_config",
        ]


class BlockConfigDefaultSerializer(serializers.Serializer):
    """
    Serializer for the default block configs payload sent by the frontend at startup.
    Only used by the sync-defaults endpoint — does NOT overwrite existing records.
    """

    frontend_id = serializers.CharField(max_length=100)
    admin_name = serializers.CharField(max_length=150)
    order = serializers.IntegerField(default=0)
    display_title = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )
    item_limit = serializers.IntegerField(default=10)
    extra_config = serializers.JSONField(default=dict)
