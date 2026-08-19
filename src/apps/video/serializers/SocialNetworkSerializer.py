"""
Esup-Pod - Social Network serializer.
"""

from rest_framework import serializers
from src.apps.video.models import SocialNetwork


class SocialNetworkSerializer(serializers.ModelSerializer):
    """Serializer for SocialNetwork model."""

    class Meta:
        """Meta options for SocialNetworkSerializer."""

        model = SocialNetwork
        fields = [
            "id",
            "name",
            "icon_name",
            "share_url_template",
            "is_active",
            "order",
        ]
        read_only_fields = ["id"]
