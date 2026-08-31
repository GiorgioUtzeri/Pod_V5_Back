"""Esup-Pod - Tests for the video files service helpers."""

import os
import tempfile
import shutil
from django.test import TestCase
from src.apps.video.services.files import duplicate_source_file


class VideoFilesServiceTests(TestCase):
    """Test cases for checking video file service utilities."""

    def setUp(self):
        """Set up temporary directory and dummy file representing a source video."""
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_file = os.path.join(self.temp_dir, "video.mp4")
        with open(self.dummy_file, "w") as f:
            f.write("dummy")

    def tearDown(self):
        """Remove temporary testing directory."""
        shutil.rmtree(self.temp_dir)

    def test_duplicate_source_file(self):
        """Test that duplicate_source_file correctly copies a video file with an identifier prefix."""
        new_name = duplicate_source_file(
            "123", self.dummy_file, "video/sources/video.mp4"
        )
        expected_path = os.path.join(self.temp_dir, "123_video.mp4")
        self.assertTrue(os.path.exists(expected_path))
        self.assertEqual(new_name, "video/sources/123_video.mp4")
