"""
Esup-Pod - Video Chapter viewset.
"""

from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from src.apps.video.models import Chapter, Video
from src.apps.video.serializers import ChapterSerializer


class ChapterViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing video chapters.
    """

    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """Filter chapters by video if video parameter is provided."""
        queryset = Chapter.objects.all()
        video_id = self.request.query_params.get("video")
        video_slug = self.request.query_params.get("video_slug")

        if video_id:
            queryset = queryset.filter(video_id=video_id)
        elif video_slug:
            queryset = queryset.filter(video__slug=video_slug)

        return queryset.select_related("video")

    def perform_create(self, serializer):
        """Validate owner/co-owner rights before creating chapter."""
        video = serializer.validated_data.get("video")
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        if (
            not user.is_superuser
            and video.owner != user
            and not video.co_owners.filter(pk=user.pk).exists()
        ):
            raise PermissionDenied(
                "You do not have permission to add chapters to this video."
            )

        serializer.save()

    def perform_update(self, serializer):
        """Validate owner/co-owner rights before updating chapter."""
        chapter = self.get_object()
        user = self.request.user
        if (
            not user.is_superuser
            and chapter.video.owner != user
            and not chapter.video.co_owners.filter(pk=user.pk).exists()
        ):
            raise PermissionDenied(
                "You do not have permission to edit chapters of this video."
            )

        serializer.save()

    def perform_destroy(self, instance):
        """Validate owner/co-owner rights before deleting chapter."""
        user = self.request.user
        if (
            not user.is_superuser
            and instance.video.owner != user
            and not instance.video.co_owners.filter(pk=user.pk).exists()
        ):
            raise PermissionDenied(
                "You do not have permission to delete chapters of this video."
            )

        instance.delete()
