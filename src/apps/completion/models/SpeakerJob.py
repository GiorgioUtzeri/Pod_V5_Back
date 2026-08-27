"""
Esup-Pod - SpeakerJob model.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class SpeakerJob(models.Model):
    """
    Model representing a job title or function for a speaker.
    """

    title = models.CharField(
        _("Title"),
        max_length=200,
        unique=True,
    )
    description = models.TextField(
        _("Description"),
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta options for SpeakerJob."""

        verbose_name = _("Speaker Job")
        verbose_name_plural = _("Speaker Jobs")
        ordering = ["title"]

    def __str__(self):
        return self.title
