"""
Esup-Pod - Social Network model for video sharing.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class SocialNetwork(models.Model):
    """
    Model representing a configurable social network share target.
    Can be managed via Django Admin.
    """

    name = models.CharField(
        _("Network Name"),
        max_length=100,
        unique=True,
        help_text=_("Name of the social network (e.g. X, Facebook, LinkedIn)."),
    )
    icon_name = models.CharField(
        _("Icon Name"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("Identifier or icon class name for frontend rendering."),
    )
    share_url_template = models.CharField(
        _("Share URL Template"),
        max_length=500,
        help_text=_(
            "URL pattern for sharing. Placeholders: {url} for video link, {title} for video title."
        ),
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this network is available for sharing across the portal."),
    )
    order = models.PositiveSmallIntegerField(
        _("Display Order"),
        default=0,
        help_text=_("Order in which the share button appears."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """SocialNetwork metadata."""

        verbose_name = _("Social Network")
        verbose_name_plural = _("Social Networks")
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Disabled'})"

    def get_share_url(self, video_url: str, title: str = "") -> str:
        """Formulate the share URL for a given video URL and title."""
        import urllib.parse

        encoded_url = urllib.parse.quote(video_url, safe="")
        encoded_title = urllib.parse.quote(title, safe="")
        return self.share_url_template.format(url=encoded_url, title=encoded_title)
