from django.test import TestCase
from src.apps.authentication.services.core import is_staff_affiliation
from unittest.mock import patch

class CoreServicesTests(TestCase):
    @patch("src.apps.authentication.services.core.auth_settings")
    def test_is_staff_affiliation(self, mock_settings):
        mock_settings.affiliation_staff = ["staff", "faculty"]
        self.assertTrue(is_staff_affiliation("staff"))
        self.assertFalse(is_staff_affiliation("student"))
