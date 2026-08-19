import os
import tempfile
import shutil
from django.test import TestCase
from src.apps.utils.files import safe_remove_file, resolve_file_field_image_url

class MockField:
    def __init__(self, path, url, name, storage):
        self.path = path
        self.url = url
        self.name = name
        self.storage = storage

class MockStorage:
    def __init__(self, existing_files):
        self.existing_files = existing_files
    
    def exists(self, name):
        return name in self.existing_files

class UtilsFilesTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dummy_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.dummy_file, "w") as f:
            f.write("test")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_safe_remove_file_exists(self):
        field = MockField(path=self.dummy_file, url="", name="", storage=None)
        safe_remove_file(field)
        self.assertFalse(os.path.exists(self.dummy_file))

    def test_safe_remove_file_not_exists(self):
        field = MockField(path=os.path.join(self.temp_dir, "nonexistent.txt"), url="", name="", storage=None)
        safe_remove_file(field)
        # Should not raise exception

    def test_resolve_file_field_image_url_vtt(self):
        storage = MockStorage(existing_files=["test.jpg"])
        field = MockField(path="", url="/media/test.vtt", name="test.vtt", storage=storage)
        url = resolve_file_field_image_url(field)
        self.assertEqual(url, "/media/test.jpg")

    def test_resolve_file_field_image_url_vtt_fallback(self):
        storage = MockStorage(existing_files=[])
        field = MockField(path="", url="/media/test.vtt", name="test.vtt", storage=storage)
        url = resolve_file_field_image_url(field)
        self.assertEqual(url, "/media/test.png")

    def test_resolve_file_field_image_url_non_vtt(self):
        field = MockField(path="", url="/media/test.mp4", name="test.mp4", storage=None)
        url = resolve_file_field_image_url(field)
        self.assertEqual(url, "/media/test.mp4")
