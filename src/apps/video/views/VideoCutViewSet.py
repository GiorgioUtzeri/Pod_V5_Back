"""
Esup-Pod - VideoCut viewset.
"""
from rest_framework import viewsets, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from src.apps.video.models import Video, VideoCut
from src.apps.video.serializers import VideoCutSerializer
from src.apps.video.conf import video_settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema

class VideoCutViewSet(viewsets.ViewSet):
    """
    ViewSet for video cut management.
    Allows creating or replacing a cut definition for a given video.
    Cleans up time-dependent related objects (chapters, notes) on update.
    """

    @extend_schema(
        summary="Create or replace a video cut",
        description="Creates or replaces a cut for the given video. time_start and time_end are in seconds.",
        request=VideoCutSerializer,
        responses={201: VideoCutSerializer},
    )

    def create(self, request, video_slug=None):
        """
        Creates or replaces a cut for the given video.
        Deletes existing time-dependent data (chapters, notes) on success.
        """
        try:
            video = Video.objects.get(slug=video_slug)
        except Video.DoesNotExist:
            raise NotFound(_("Video not found."))

        is_owner = video.owner == request.user
        is_co_owner = video.co_owners.filter(pk=request.user.pk).exists()
        if not (is_owner or is_co_owner or request.user.is_superuser):
            raise PermissionDenied(_("You do not have permission to cut this video."))

        if video_settings.restrict_edit_to_staff and not request.user.is_staff:
            raise PermissionDenied(_("Only staff members are allowed to cut videos."))

        serializer = VideoCutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        VideoCut.objects.filter(video=video).delete()
        video_cut = serializer.save(video=video)

        if hasattr(video, "chapters"):
            video.chapters.all().delete()
        if hasattr(video, "notes"):
            video.notes.all().delete()

        return Response(
            VideoCutSerializer(video_cut).data,
            status=status.HTTP_201_CREATED,
        )
    
    @extend_schema(
        summary="Delete a video cut",
        description="Deletes the cut associated with the given video.",
        responses={204: None},
    )
    def destroy(self, request, video_slug=None):
        """Deletes the cut associated with the given video."""
        try:
            video = Video.objects.get(slug=video_slug)
        except Video.DoesNotExist:
            raise NotFound(_("Video not found."))

        is_owner = video.owner == request.user
        is_co_owner = video.co_owners.filter(pk=request.user.pk).exists()
        if not (is_owner or is_co_owner or request.user.is_superuser):
            raise PermissionDenied(_("You do not have permission to delete this cut."))

        if video_settings.restrict_edit_to_staff and not request.user.is_staff:
            raise PermissionDenied(_("Only staff members are allowed to delete cuts."))

        try:
            video.cut.delete()
        except VideoCut.DoesNotExist:
            raise NotFound(_("No cut found for this video."))

        return Response(status=status.HTTP_204_NO_CONTENT)