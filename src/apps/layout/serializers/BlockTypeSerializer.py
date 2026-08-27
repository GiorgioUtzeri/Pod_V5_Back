"""
Esup-Pod - BlockType serializer.
"""

from rest_framework import serializers
from src.apps.layout.models import BlockType


class BlockTypeSerializer(serializers.ModelSerializer):
    """Serializer for BlockType — used for list and register endpoints."""

    class Meta:
        """Meta options."""

        model = BlockType
        fields = [
            "frontend_id",
            "name",
            "description",
            "fields_schema",
            "version",
            "updated_at",
        ]


class BlockTypeRegisterSerializer(serializers.Serializer):
    """
    Serializer for the bulk register payload sent by the frontend at startup.
    Accepts a list of block type manifests.
    """

    frontend_id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(allow_blank=True, default="")
    fields_schema = serializers.JSONField(default=dict)
    version = serializers.CharField(max_length=20, default="1.0.0")
