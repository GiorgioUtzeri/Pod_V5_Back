"""
Esup-Pod - Video models tests.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from src.apps.video.models import Video, ViewCount, Comment, VideoHyperlink
import datetime

User = get_user_model()


class VideoModelTests(TestCase):
    """
    Esup-Pod - Tests for the Video application models.
    """

    def setUp(self):
        """Sets up a video and an owner for model testing."""
        self.user = User.objects.create_user(username="owner", password="password")
        self.video = Video.objects.create(
            title="Model Test Video",
            owner=self.user,
            description="A description",
            status=Video.Status.PUBLISHED,
            license=Video.License.CC_BY,
        )

    def test_get_dublin_core(self):
        """Verifies the Dublin Core metadata generation."""
        dc = self.video.get_dublin_core()
        self.assertEqual(dc["title"], "Model Test Video")
        self.assertEqual(dc["description"], "A description")
        self.assertEqual(dc["creator"], "owner")
        self.assertEqual(dc["format"], "video/mp4")
        self.assertEqual(dc["rights"], Video.License.CC_BY)

    def test_view_count_creation(self):
        """Verifies daily view count records and their string representation."""
        view_count = ViewCount.objects.create(
            video=self.video, date=datetime.date(2026, 1, 1), count=5
        )
        self.assertEqual(view_count.video, self.video)
        self.assertEqual(view_count.count, 5)
        self.assertEqual(str(view_count), "Model Test Video - 2026-01-01: 5")

    def test_video_str(self):
        """Verifies the video's string representation."""
        self.assertEqual(str(self.video), "Model Test Video (Published (Public))")

    def test_create_video_hyperlink(self):
        """Verifies that a VideoHyperlink can be created and linked to a video."""
        VideoHyperlink.objects.create(
            video=self.video,
            url="https://example.com",
            text="Example",
            time_start=10,
            time_end=30,
        )
        self.assertEqual(self.video.hyperlinks.count(), 1)
        self.assertEqual(self.video.hyperlinks.first().url, "https://example.com")
        self.assertEqual(self.video.hyperlinks.first().text, "Example")

    def test_video_hyperlink_str(self):
        """Verifies the string representation of a VideoHyperlink."""
        self.assertEqual(
            str(
                VideoHyperlink.objects.create(
                    video=self.video,
                    url="https://example.com",
                    text="Example",
                    time_start=10,
                    time_end=30,
                )
            ),
            "Model Test Video - Example (10s -> 30s)",
        )

    def test_video_hyperlink_optional_fields(self):
        """Verifies that icon and position are optional."""
        hyperlink = VideoHyperlink.objects.create(
            video=self.video,
            url="https://example.com",
            text="No icon",
            time_start=0,
            time_end=10,
        )
        self.assertIsNone(hyperlink.icon)
        self.assertIsNone(hyperlink.position)

    def test_video_hyperlink_ordering(self):
        """Verifies that hyperlinks are ordered by time_start."""
        VideoHyperlink.objects.create(
            video=self.video, url="https://b.com", text="B", time_start=20, time_end=40
        )
        VideoHyperlink.objects.create(
            video=self.video, url="https://a.com", text="A", time_start=5, time_end=15
        )
        hyperlinks = list(self.video.hyperlinks.all())
        self.assertEqual(hyperlinks[0].text, "A")
        self.assertEqual(hyperlinks[1].text, "B")

    def test_video_hyperlink_cascade_delete(self):
        """Verifies that hyperlinks are deleted when the video is deleted."""
        VideoHyperlink.objects.create(
            video=self.video,
            url="https://example.com",
            text="Gone",
            time_start=0,
            time_end=5,
        )
        self.assertEqual(VideoHyperlink.objects.count(), 1)
        self.video.delete()
        self.assertEqual(VideoHyperlink.objects.count(), 0)


class CommentBasicTests(TestCase):
    """Esup-Pod - Tests for the Comment model."""

    def setUp(self):
        """Sets up a video and a user for comment testing."""
        self.user = User.objects.create_user(username="commenter2", password="password")
        self.video = Video.objects.create(
            title="A Video", owner=self.user, status=Video.Status.PUBLISHED
        )

    def test_create_comment(self):
        """Verifies the creation of a comment."""
        comment = Comment.objects.create(
            author=self.user, video=self.video, content="Small test comment"
        )
        self.assertEqual(str(comment), "Small test comment")
        self.assertEqual(comment.number_vote, 0)
