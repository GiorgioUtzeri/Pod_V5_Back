"""
Esup-Pod - BlockType model.

A BlockType describes a *kind* of block that the frontend knows how to render.
It is registered automatically by the frontend at startup and is read-only in the admin.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BlockType(models.Model):
    """
    Represents a type of frontend block registered by the Next.js frontend at startup.

    The frontend scans its `BlockRegistry` (manifests) and calls
    `POST /api/layout/block-types/register/` to upsert these records.
    Admins can *read* these in Django admin to understand what blocks are available,
    then create `BlockConfig` instances referencing them.
    """

    frontend_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Frontend Identifier"),
        help_text=_(
            "Unique identifier matching the frontend component key (e.g., 'collection-block')."
        ),
    )

    name = models.CharField(
        max_length=150,
        verbose_name=_("Block Name"),
        help_text=_("Human-readable name shown in the Django admin."),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("What this block displays and how it behaves."),
    )

    fields_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Fields Schema"),
        help_text=_(
            "JSON description of configurable fields (labels, types, options, defaults). "
            "Used by the admin widget to render a dynamic form."
        ),
    )

    version = models.CharField(
        max_length=20,
        default="1.0.0",
        verbose_name=_("Version"),
        help_text=_("Manifest version sent by the frontend. Updated on every sync."),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    def __str__(self):
        return f"{self.name} ({self.frontend_id}) v{self.version}"

    class Meta:
        """Meta options."""

        verbose_name = _("Block Type")
        verbose_name_plural = _("Block Types")
        ordering = ["name"]
