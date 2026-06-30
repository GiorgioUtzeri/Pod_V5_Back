"""
Esup-Pod - Video completion link tests.
"""

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from rest_framework.test import APITestCase

from src.apps.completion.models import Contribution, Contributor, Document, Overlay
from src.apps.video.apps import sync_metadata
from src.apps.video.models import Video

User = get_user_model()


class VideoCompletionLinkTests(APITestCase):
    """Tests for completion data exposed via VideoSerializer."""

    def setUp(self):
        """Sets up a video with linked contribution, overlay, and document."""
        sync_metadata(sender=None)
        self.site = Site.objects.get_current()
        self.user = User.objects.create_user(username="owner", password="password")
        self.video = Video.objects.create(
            title="Completion Test Video",
            owner=self.user,
            status=Video.Status.PUBLISHED,
        )
        self.video.sites.add(self.site)

        self.contributor = Contributor.objects.create(
            first_name="John",
            last_name="Doe",
        )
        Contribution.objects.create(
            video=self.video,
            contributor=self.contributor,
            role="author",
        )
        Overlay.objects.create(
            video=self.video,
            title="Test Overlay",
            time_start=5,
            time_end=10,
            content="<p>Hello</p>",
        )
        Document.objects.create(
            video=self.video,
            title="Test Document",
            file="documents/test.pdf",
        )

    def test_video_detail_includes_completion_data(self):
        """Verifies that GET /api/videos/{slug}/ includes contributions, overlays, documents."""
        url = f"/api/videos/{self.video.slug}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["contributions"]), 1)
        self.assertEqual(
            response.data["contributions"][0]["contributor_details"]["first_name"],
            "John",
        )
        self.assertEqual(len(response.data["overlays"]), 1)
        self.assertEqual(response.data["overlays"][0]["title"], "Test Overlay")
        self.assertEqual(len(response.data["documents"]), 1)
        self.assertEqual(response.data["documents"][0]["title"], "Test Document")
