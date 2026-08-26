"""Esup-Pod - Tests for the comparesettings management command."""

from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch
import os
import tempfile
import json


class CompareSettingsTests(TestCase):
    """Test cases for the comparesettings management command validation."""

    def setUp(self):
        """Create a temporary file for use during test cases."""
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".json"
        )
        self.temp_file.close()

    def tearDown(self):
        """Clean up the temporary file after testing."""
        os.unlink(self.temp_file.name)

    @patch("os.path.join")
    @patch("os.path.exists", return_value=False)
    def test_comparesettings_no_file(self, mock_exists, mock_join):
        """Test that command exits with status 1 if the JSON settings file is missing."""
        with self.assertRaises(SystemExit) as cm:
            call_command("comparesettings")
        self.assertEqual(cm.exception.code, 1)

    @patch("src.apps.core.management.commands.comparesettings.dir")
    @patch("os.path.join")
    def test_comparesettings_success(self, mock_join, mock_dir):
        """Test that command succeeds when settings in code match the JSON descriptions."""
        mock_join.return_value = self.temp_file.name
        mock_dir.return_value = ["MY_SETTING", "GLOBAL_SET"]

        with open(self.temp_file.name, "w") as f:
            json.dump(
                [
                    {
                        "configuration_apps": {
                            "description": {"app1": {"settings": {"MY_SETTING": {}}}},
                            "settings": {"GLOBAL_SET": {}},
                        }
                    }
                ],
                f,
            )

        call_command("comparesettings")  # should succeed

    @patch("src.apps.core.management.commands.comparesettings.dir")
    @patch("os.path.join")
    def test_comparesettings_missing_in_json(self, mock_join, mock_dir):
        """Test that command exits with status 1 if a setting in code is missing from the JSON file."""
        mock_join.return_value = self.temp_file.name
        mock_dir.return_value = ["MY_SETTING", "EXTRA_CODE_SETTING"]

        with open(self.temp_file.name, "w") as f:
            json.dump(
                [
                    {
                        "configuration_apps": {
                            "description": {"app1": {"settings": {"MY_SETTING": {}}}}
                        }
                    }
                ],
                f,
            )

        with self.assertRaises(SystemExit) as cm:
            call_command("comparesettings")
        self.assertEqual(cm.exception.code, 1)
