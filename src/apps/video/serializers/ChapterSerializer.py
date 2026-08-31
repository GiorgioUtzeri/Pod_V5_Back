"""
Esup-Pod - Video Chapter serializer.
"""

from rest_framework import serializers
from src.apps.video.models import Chapter


class ChapterSerializer(serializers.ModelSerializer):
    """Serializer for Chapter model."""

    class Meta:
        """Meta options for ChapterSerializer."""

        model = Chapter
        fields = [
            "id",
            "video",
            "title",
            "time_start",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
