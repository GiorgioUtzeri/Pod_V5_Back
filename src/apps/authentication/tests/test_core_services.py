"""Esup-Pod - Tests for the authentication core services."""

from django.test import TestCase
from src.apps.authentication.services.core import is_staff_affiliation
from unittest.mock import patch


class CoreServicesTests(TestCase):
    """Test cases for core authentication helper functions."""

    @patch("src.apps.authentication.services.core.auth_settings")
    def test_is_staff_affiliation(self, mock_settings):
        """Test that is_staff_affiliation correctly checks if the affiliation is considered staff."""
        mock_settings.affiliation_staff = ["staff", "faculty"]
        self.assertTrue(is_staff_affiliation("staff"))
        self.assertFalse(is_staff_affiliation("student"))
