"""
Esup-Pod - ViewSet for the VideoHyperlink model.
- Read: Allowed for everyone (or based on global config).
- Write/Delete: Allowed only if the user is the owner of the linked video.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from src.apps.video.models import VideoHyperlink
from src.apps.video.serializers import VideoHyperlinkSerializer


class VideoHyperlinkViewSet(viewsets.ModelViewSet):
    """
    Esup-Pod - Provides CRUD operations for VideoHyperlink objects.
    Supports filtering by video_id via query parameter.
    """

    queryset = VideoHyperlink.objects.select_related("video").all()
    serializer_class = VideoHyperlinkSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Returns hyperlinks filtered by video_id query parameter if provided."""
        queryset = super().get_queryset()
        video_id = self.request.query_params.get("video_id")
        if video_id:
            queryset = queryset.filter(video_id=video_id)
        return queryset
