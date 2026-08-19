from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch
import os
import tempfile
import json


class CompareSettingsTests(TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".json"
        )
        self.temp_file.close()

    def tearDown(self):
        os.unlink(self.temp_file.name)

    @patch("os.path.join")
    @patch("os.path.exists", return_value=False)
    def test_comparesettings_no_file(self, mock_exists, mock_join):
        with self.assertRaises(SystemExit) as cm:
            call_command("comparesettings")
        self.assertEqual(cm.exception.code, 1)

    @patch("src.apps.core.management.commands.comparesettings.dir")
    @patch("os.path.join")
    def test_comparesettings_success(self, mock_join, mock_dir):
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
