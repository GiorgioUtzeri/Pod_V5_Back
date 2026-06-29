"""
Esup-Pod - Bulk actions tests.
"""

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from src.apps.video.apps import sync_metadata
from src.apps.video.models import Video

User = get_user_model()


class BulkActionsTests(APITestCase):
    """Tests for the bulk_actions endpoint."""

    def setUp(self):
        """Sets up users, site, and videos for bulk action testing."""
        sync_metadata(sender=None)
        self.client = APIClient()
        self.site = Site.objects.get_current()

        self.owner = User.objects.create_user(username="owner", password="password")
        self.other_user = User.objects.create_user(username="other", password="password")

        self.video1 = Video.objects.create(
            title="Video 1",
            owner=self.owner,
            status=Video.Status.DRAFT,
        )
        self.video1.sites.add(self.site)

        self.video2 = Video.objects.create(
            title="Video 2",
            owner=self.owner,
            status=Video.Status.DRAFT,
        )
        self.video2.sites.add(self.site)

        self.other_video = Video.objects.create(
            title="Other Video",
            owner=self.other_user,
            status=Video.Status.PUBLISHED,
        )
        self.other_video.sites.add(self.site)

    def test_bulk_delete_own_videos(self):
        """Owner can bulk delete their own videos."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            "/api/videos/bulk/",
            {"video_ids": [self.video1.id, self.video2.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Video.objects.filter(id=self.video1.id).exists())
        self.assertFalse(Video.objects.filter(id=self.video2.id).exists())

    def test_bulk_delete_other_user_videos_forbidden(self):
        """User cannot bulk delete videos they don't own."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            "/api/videos/bulk/",
            {"video_ids": [self.other_video.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Video.objects.filter(id=self.other_video.id).exists())

    def test_bulk_patch_own_videos(self):
        """Owner can bulk patch their own videos."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            "/api/videos/bulk/",
            {
                "video_ids": [self.video1.id, self.video2.id],
                "fields": {"allow_downloading": True},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 2)
        self.assertTrue(Video.objects.get(id=self.video1.id).allow_downloading)
        self.assertTrue(Video.objects.get(id=self.video2.id).allow_downloading)

    def test_bulk_patch_excluded_field_rejected(self):
        """Bulk patch with excluded fields is rejected."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            "/api/videos/bulk/",
            {"video_ids": [self.video1.id], "fields": {"title": "New Title"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_no_videos_selected(self):
        """Empty video_ids returns 400."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            "/api/videos/bulk/",
            {"video_ids": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_video_not_found(self):
        """Non-existent video IDs return 404."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(
            "/api/videos/bulk/",
            {"video_ids": [99999]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_unauthenticated(self):
        """Unauthenticated users cannot use bulk actions."""
        response = self.client.delete(
            "/api/videos/bulk/",
            {"video_ids": [self.video1.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bulk_patch_no_fields(self):
        """Bulk patch without fields returns 400."""
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            "/api/videos/bulk/",
            {"video_ids": [self.video1.id], "fields": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
