"""
Esup-Pod - Tests for Video duplication.
"""

import os
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from src.apps.video.models import Video

User = get_user_model()


class VideoDuplicationTests(APITestCase):
    """
    Tests for video duplication API endpoint.
    """

    def setUp(self):
        """
        Setup test users, site, and an initial video.
        """
        self.user = User.objects.create_user(
            username="testuser", password="password"
        )  # nosec
        self.other_user = User.objects.create_user(
            username="otheruser", password="password"
        )
        self.site = Site.objects.get_current()

        # Create a dummy video file
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_video_path = os.path.join(self.temp_dir, "test.mp4")
        with open(self.dummy_video_path, "wb") as f:
            f.write(b"dummy video content")

        self.video_file = SimpleUploadedFile(
            "test.mp4", b"dummy video content", content_type="video/mp4"
        )

        self.video = Video.objects.create(
            title="Original Video",
            owner=self.user,
            status=Video.Status.PUBLISHED,
        )
        self.video.sites.set([self.site])
        # Save the file using the field's save method to ensure it's in the proper storage
        self.video.video_file.save("test.mp4", self.video_file)

        from src.apps.video.conf import video_settings

        video_settings.use_duplicate = True

    def test_duplicate_video_success(self):
        """
        Test successful duplication of a video by its owner.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("video-duplicate", kwargs={"slug": self.video.slug})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        duplicated_slug = response.data["slug"]
        duplicated_video = Video.objects.get(slug=duplicated_slug)

        self.assertEqual(duplicated_video.title, f"Copy of {self.video.title}")
        self.assertEqual(duplicated_video.status, Video.Status.DRAFT)
        self.assertEqual(duplicated_video.owner, self.user)
        self.assertFalse(bool(duplicated_video.video_file))

    def test_duplicate_video_unauthorized(self):
        """
        Test that an unauthenticated user cannot duplicate a video.
        """
        # Unauthenticated user
        url = reverse("video-duplicate", kwargs={"slug": self.video.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_video_forbidden(self):
        """
        Test that a user who is not the owner cannot duplicate the video.
        """
        # Authenticated but not owner
        self.client.force_authenticate(user=self.other_user)
        url = reverse("video-duplicate", kwargs={"slug": self.video.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_video_disabled(self):
        """
        Test that duplication fails if use_duplicate setting is False.
        """
        from src.apps.video.conf import video_settings

        video_settings.use_duplicate = False

        self.client.force_authenticate(user=self.user)
        url = reverse("video-duplicate", kwargs={"slug": self.video.slug})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Duplication is disabled.")

        # Re-enable for other tests
        video_settings.use_duplicate = True

    def test_duplicate_source_file(self):
        """
        Test physical duplication of a video source file on disk.
        """
        from src.apps.video.services.files import duplicate_source_file
        import shutil

        os.makedirs(self.temp_dir, exist_ok=True)
        src_path = os.path.join(self.temp_dir, "source.mp4")
        with open(src_path, "wb") as f:
            f.write(b"video source content")

        original_name = "videos/sources/source.mp4"
        new_name = duplicate_source_file(
            video_id=42, src_path=src_path, original_name=original_name
        )

        expected_new_path = os.path.join(self.temp_dir, "42_source.mp4")
        self.assertTrue(os.path.exists(expected_new_path))
        self.assertEqual(new_name, "videos/sources/42_source.mp4")

        try:
            shutil.rmtree(self.temp_dir)
        except OSError:
            pass

    def test_assign_default_site(self):
        """
        Test assignment of a default site to a video.
        """
        from src.apps.video.services.sites import assign_default_site
        from django.test import override_settings

        # Test when sites exist already
        video_with_site = Video.objects.create(
            title="Video with site",
            owner=self.user,
        )
        video_with_site.sites.add(self.site)
        assign_default_site(video_with_site)
        self.assertEqual(video_with_site.sites.count(), 1)

        # Test when no site is set (assign default via fallback)
        video_no_site = Video.objects.create(
            title="Video without site",
            owner=self.user,
        )
        video_no_site.sites.clear()
        from django.core.exceptions import ImproperlyConfigured

        with override_settings(SITE_ID=None):
            with self.assertRaises(ImproperlyConfigured):
                assign_default_site(video_no_site)

        # Test when SITE_ID is set (use SITE_ID)
        video_with_site_id = Video.objects.create(
            title="Video with site ID",
            owner=self.user,
        )
        video_with_site_id.sites.clear()
        with override_settings(SITE_ID=self.site.id):
            assign_default_site(video_with_site_id)
        self.assertTrue(video_with_site_id.sites.filter(id=self.site.id).exists())

    def test_generate_unique_slug_collision(self):
        """
        Test slug collision loop in generate_unique_slug.
        """
        from src.apps.video.services.slug import generate_unique_slug

        # Create a video with target slug
        Video.objects.create(
            title="Colliding Video",
            slug="collision-slug",
            owner=self.user,
        )
        new_slug = generate_unique_slug("collision-slug")
        self.assertEqual(new_slug, "collision-slug-1")
