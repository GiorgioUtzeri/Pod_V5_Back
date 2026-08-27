"""
Esup-Pod - BlockConfig model.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class BlockConfig(models.Model):
    """
    A concrete *instance* of a block placed on a page.

    Admins create these in Django admin by choosing a block type and configuring
    its parameters (title, item_limit, extra_config, etc.).
    Multiple instances of the same `frontend_id` (block type) can coexist on a page
    with different configurations (e.g., two collection blocks — one for channels,
    one for themes).
    """

    block_type = models.ForeignKey(
        "layout.BlockType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="instances",
        verbose_name=_("Block Type"),
        help_text=_(
            "The block type this instance is based on. "
            "Drives the visual configuration editor in admin."
        ),
    )

    frontend_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Frontend Identifier"),
        help_text=_(
            "The ID matching the frontend block component (e.g., 'collection-block'). "
            "Multiple instances of the same frontend_id are allowed."
        ),
    )

    admin_name = models.CharField(
        max_length=150,
        verbose_name=_("Admin Name"),
        help_text=_("Readable label to distinguish this instance in Django administration."),
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Display sequence order for the frontend layout."),
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this block should be displayed by the frontend."),
    )

    display_title = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Display Title")
    )

    subtitle_or_text = models.TextField(
        blank=True, null=True, verbose_name=_("Subtitle or Text")
    )

    item_limit = models.PositiveSmallIntegerField(
        default=10,
        verbose_name=_("Item Limit"),
        help_text=_(
            "How many items (e.g., videos) should the frontend request for this block."
        ),
    )

    background_color = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Background Color (Hex)")
    )

    text_color = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Text Color (Hex)")
    )

    extra_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Extra Configuration (JSON)"),
        help_text=_("Additional frontend-specific options (e.g., collection_type, order_by)."),
    )

    def __str__(self):
        return f"[{self.order}] {self.admin_name} ({self.frontend_id})"

    class Meta:
        """Meta options."""

        verbose_name = _("Block Configuration")
        verbose_name_plural = _("Block Configurations")
        ordering = ["order", "frontend_id"]
