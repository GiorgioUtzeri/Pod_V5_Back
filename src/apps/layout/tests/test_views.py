"""
Esup-Pod - Layout tests.
"""

from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from src.apps.layout.models import BlockConfig


class BlockConfigAPITests(APITestCase):
    """Test suite for BlockConfig API endpoints."""

    def setUp(self):
        """Set up test environment and create sample BlockConfig."""
        self.block_config = BlockConfig.objects.create(
            frontend_id="test-carousel",
            admin_name="Test Carousel",
            is_active=True,
            display_title="Test Block",
            item_limit=5,
            order=1,
        )

    def test_list_blocks(self):
        """Test retrieving the list of blocks."""
        url = reverse("blockconfig-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data["results"] if "results" in data else data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["frontend_id"], "test-carousel")
        self.assertEqual(results[0]["display_title"], "Test Block")
        self.assertEqual(results[0]["item_limit"], 5)

    def test_retrieve_block(self):
        """Test retrieving a single block by frontend_id."""
        url = reverse("blockconfig-detail", args=[self.block_config.frontend_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["frontend_id"], "test-carousel")
        self.assertEqual(data["display_title"], "Test Block")

    def test_layout_settings_flag(self):
        """Test that blocks are not returned if USE_LAYOUT_BLOCKS is False."""
        with self.settings(USE_LAYOUT_BLOCKS=False):
            url = reverse("blockconfig-list")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            results = data["results"] if "results" in data else data
            self.assertEqual(len(results), 0)
