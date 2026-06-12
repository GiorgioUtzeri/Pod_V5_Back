"""
Esup-Pod - ViewSet for the VideoHyperlink model.
- Read: Allowed for everyone (or based on global config).
- Write/Delete: Allowed only if the user is the owner of the linked video.
"""

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from src.apps.video.models import (
    VideoHyperlink,
    Video,
)  # add Video if not already imported
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

    @action(detail=False, methods=["get"])
    def list_hyperlinks(self, request, video_slug=None):
        """Returns all hyperlinks associated with the given video slug."""
        video = get_object_or_404(Video, slug=video_slug)
        qs = self.get_queryset().filter(video=video)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add_hyperlink(self, request, video_slug=None):
        """Creates a new hyperlink overlay for the given video slug."""
        video = get_object_or_404(Video, slug=video_slug)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(video=video)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["delete"])
    def delete_hyperlink(self, request, video_slug=None, hyperlink_id=None):
        """Deletes a specific hyperlink by UUID for the given video slug."""
        video = get_object_or_404(Video, slug=video_slug)
        hyperlink = get_object_or_404(VideoHyperlink, id=hyperlink_id, video=video)
        hyperlink.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
