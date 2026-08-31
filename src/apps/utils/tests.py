"""Esup-Pod - Tests for utility helper functions related to file operations."""

import os
import tempfile
import shutil
from django.test import TestCase
from src.apps.utils.files import safe_remove_file, resolve_file_field_image_url


class MockField:
    """Mock representation of a Django FileField or ImageField for testing."""

    def __init__(self, path, url, name, storage):
        """Initialize mock field attributes."""
        self.path = path
        self.url = url
        self.name = name
        self.storage = storage


class MockStorage:
    """Mock storage system to simulate file existence checks."""

    def __init__(self, existing_files):
        """Initialize mock storage with a list of existing files."""
        self.existing_files = existing_files

    def exists(self, name):
        """Return True if the specified file exists in the mock storage."""
        return name in self.existing_files


class UtilsFilesTests(TestCase):
    """Test cases for checking custom file manipulation helper utilities."""

    def setUp(self):
        """Set up temporary directory and dummy file for path-based testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.dummy_file, "w") as f:
            f.write("test")

    def tearDown(self):
        """Remove temporary directory created for testing."""
        shutil.rmtree(self.temp_dir)

    def test_safe_remove_file_exists(self):
        """Test that safe_remove_file correctly deletes an existing file."""
        field = MockField(path=self.dummy_file, url="", name="", storage=None)
        safe_remove_file(field)
        self.assertFalse(os.path.exists(self.dummy_file))

    def test_safe_remove_file_not_exists(self):
        """Test that safe_remove_file does not fail when target file is missing."""
        field = MockField(
            path=os.path.join(self.temp_dir, "nonexistent.txt"),
            url="",
            name="",
            storage=None,
        )
        safe_remove_file(field)
        # Should not raise exception

    def test_resolve_file_field_image_url_vtt(self):
        """Test resolving vtt file image url when corresponding jpg exists."""
        storage = MockStorage(existing_files=["test.jpg"])
        field = MockField(
            path="", url="/media/test.vtt", name="test.vtt", storage=storage
        )
        url = resolve_file_field_image_url(field)
        self.assertEqual(url, "/media/test.jpg")

    def test_resolve_file_field_image_url_vtt_fallback(self):
        """Test resolving vtt file image url with png fallback when jpg does not exist."""
        storage = MockStorage(existing_files=[])
        field = MockField(
            path="", url="/media/test.vtt", name="test.vtt", storage=storage
        )
        url = resolve_file_field_image_url(field)
        self.assertEqual(url, "/media/test.png")

    def test_resolve_file_field_image_url_non_vtt(self):
        """Test resolving file field image url for non-vtt files returns original url."""
        field = MockField(path="", url="/media/test.mp4", name="test.mp4", storage=None)
        url = resolve_file_field_image_url(field)
        self.assertEqual(url, "/media/test.mp4")
