"""
Esup-Pod - Layout configuration settings.
"""

from django.conf import settings


class LayoutSettings:
    """Settings for the Layout application."""

    @property
    def use_layout_blocks(self) -> bool:
        """Return True if layout blocks are enabled."""
        return getattr(settings, "USE_LAYOUT_BLOCKS", True)

    @property
    def enable_calendar_view(self) -> bool:
        return getattr(settings, "ENABLE_CALENDAR_VIEW", False)

    @property
    def enable_frontend_channel_editing(self) -> bool:
        return getattr(settings, "ENABLE_FRONTEND_CHANNEL_EDITING", False)

    @property
    def enable_admin_shortcuts(self) -> bool:
        return getattr(settings, "ENABLE_ADMIN_SHORTCUTS", False)

    @property
    def enable_draft_live_preview(self) -> bool:
        return getattr(settings, "ENABLE_DRAFT_LIVE_PREVIEW", False)


layout_settings = LayoutSettings()
