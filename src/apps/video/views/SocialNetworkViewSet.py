"""
Esup-Pod - Social Network viewset.
"""

from rest_framework import viewsets, permissions
from src.apps.video.models import SocialNetwork
from src.apps.video.serializers import SocialNetworkSerializer


class SocialNetworkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for retrieving active social networks for share buttons.
    Read-only for normal users; management done via Django Admin.
    """

    serializer_class = SocialNetworkSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """Return active social networks ordered by display priority."""
        return SocialNetwork.objects.filter(is_active=True).order_by("order", "name")
