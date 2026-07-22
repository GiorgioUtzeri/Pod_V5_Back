"""
Esup-Pod - Video Chapter model.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from .Video import Video


class Chapter(models.Model):
    """
    Model representing a chapter in a video.
    """

    video = models.ForeignKey(
        Video,
        related_name="chapters",
        on_delete=models.CASCADE,
        verbose_name=_("Video"),
    )
    title = models.CharField(
        _("Chapter Title"),
        max_length=250,
        help_text=_("Title or description of the chapter."),
    )
    time_start = models.PositiveIntegerField(
        _("Start Time (s)"),
        default=0,
        help_text=_("Start time of the chapter in seconds."),
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        """Chapter model metadata."""

        verbose_name = _("Chapter")
        verbose_name_plural = _("Chapters")
        ordering = ["time_start"]

    def __str__(self):
        return f"{self.video.title} - {self.time_start}s: {self.title}"
