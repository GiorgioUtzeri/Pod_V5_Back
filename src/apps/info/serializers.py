"""
Esup-Pod - Serializers for info app.
"""

from rest_framework import serializers
from django.contrib.flatpages.models import FlatPage


class FlatPageSerializer(serializers.ModelSerializer):
    """Serializer for FlatPage model."""

    class Meta:
        """Meta options."""

        model = FlatPage
        fields = ["id", "url", "title", "content"]
