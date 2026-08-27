"""
Esup-Pod - Amorce model (Web TV mode).
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from src.apps.encoding.services.storage import get_storage_path_amorce

class Amorce(models.Model):
    """
    Model representing an Amorce (video bumper/intro).
    """

    title = models.CharField(
        _("Title"),
        max_length=250,
    )
    
    video_file = models.FileField(
        _("Amorce Video File"),
        upload_to=get_storage_path_amorce,
        max_length=255,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Amorce")
        verbose_name_plural = _("Amorces")

    def __str__(self):
        return self.title
