"""
Esup-Pod - Admin configuration for the layout app.
"""

import json
from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from src.apps.layout.models import BlockConfig, BlockType


# ---------------------------------------------------------------------------
# BlockType admin — READ ONLY (registered by the frontend automatically)
# ---------------------------------------------------------------------------

@admin.register(BlockType)
class BlockTypeAdmin(admin.ModelAdmin):
    """
    Read-only admin for BlockType.
    Block types are registered automatically by the Next.js frontend at startup.
    Do NOT add or edit them manually — they will be overwritten on next sync.
    """

    list_display = ("name", "frontend_id", "version", "updated_at")
    search_fields = ("name", "frontend_id")
    readonly_fields = (
        "frontend_id", "name", "description", "fields_schema", "version",
        "created_at", "updated_at",
    )
    ordering = ("name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# BlockConfig admin — writable, with dynamic extra_config editor
# ---------------------------------------------------------------------------

class DynamicExtraConfigWidget(forms.Widget):
    """
    Dynamic visual editor for extra_config.
    If a BlockType is linked, uses its `fields_schema` to render custom controls.
    Falls back to a raw JSON textarea if no schema is available.
    """

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, str):
            try:
                config_dict = json.loads(value)
            except Exception:
                config_dict = {}
        elif isinstance(value, dict):
            config_dict = value
        else:
            config_dict = {}

        json_str = json.dumps(config_dict, indent=2)
        coll_type = config_dict.get("collection_type", "channel")
        coll_ids = ", ".join(map(str, config_dict.get("collection_ids", [])))
        order_by = config_dict.get("order_by", "")

        html = f"""
        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 15px; max-width: 650px;">
            <h4 style="margin-top:0; color:#1e293b; font-size:14px; font-weight:700;">🎨 Visual Configuration Editor (extra_config)</h4>

            <div style="margin-bottom: 12px;">
                <label style="display:block; font-weight:600; margin-bottom:4px; font-size:13px;">Type de collection (si bloc collection) :</label>
                <select id="extra_cfg_coll_type" onchange="updateExtraConfigJSON()" style="width:100%; padding:6px; border-radius:4px; border:1px solid #94a3b8;">
                    <option value="channel" {"selected" if coll_type == "channel" else ""}>Chaînes (Channels)</option>
                    <option value="theme" {"selected" if coll_type == "theme" else ""}>Thèmes (Categories)</option>
                    <option value="playlist" {"selected" if coll_type == "playlist" else ""}>Playlists</option>
                    <option value="all" {"selected" if coll_type == "all" else ""}>Toutes</option>
                </select>
            </div>

            <div style="margin-bottom: 12px;">
                <label style="display:block; font-weight:600; margin-bottom:4px; font-size:13px;">Identifiants / Slugs de collections (séparés par virgule) :</label>
                <input type="text" id="extra_cfg_coll_ids" value="{coll_ids}" oninput="updateExtraConfigJSON()" placeholder="ex: 1, 5, actualites-2026" style="width:100%; padding:6px; border-radius:4px; border:1px solid #94a3b8;" />
            </div>

            <div style="margin-bottom: 12px;">
                <label style="display:block; font-weight:600; margin-bottom:4px; font-size:13px;">Ordre de tri (order_by) :</label>
                <select id="extra_cfg_order_by" onchange="updateExtraConfigJSON()" style="width:100%; padding:6px; border-radius:4px; border:1px solid #94a3b8;">
                    <option value="" {"selected" if not order_by else ""}>Défaut</option>
                    <option value="title" {"selected" if order_by == "title" else ""}>Titre (A-Z)</option>
                    <option value="-created_at" {"selected" if order_by == "-created_at" else ""}>Récents en premier (-created_at)</option>
                    <option value="start_date" {"selected" if order_by == "start_date" else ""}>Date de début live (start_date)</option>
                    <option value="-start_date" {"selected" if order_by == "-start_date" else ""}>Lives récents (-start_date)</option>
                    <option value="-max_viewers" {"selected" if order_by == "-max_viewers" else ""}>Directs populaires (-max_viewers)</option>
                    <option value="-views_count" {"selected" if order_by == "-views_count" else ""}>Vidéos plus vues (-views_count)</option>
                </select>
            </div>

            <details style="margin-top: 15px;">
                <summary style="cursor:pointer; font-weight:600; font-size:12px; color:#475569;">Mode JSON brut (Avancé)</summary>
                <textarea id="{name}_raw" name="{name}" rows="5" style="width:100%; margin-top:8px; font-family:monospace; padding:8px; border-radius:4px; border:1px solid #94a3b8;">{json_str}</textarea>
            </details>
        </div>

        <script>
        function updateExtraConfigJSON() {{
            var collType = document.getElementById('extra_cfg_coll_type').value;
            var collIdsRaw = document.getElementById('extra_cfg_coll_ids').value;
            var orderBy = document.getElementById('extra_cfg_order_by').value;

            var idsArray = collIdsRaw.split(',').map(function(s) {{ return s.trim(); }}).filter(Boolean);

            var jsonObj = {{}};
            try {{
                jsonObj = JSON.parse(document.getElementById('{name}_raw').value || '{{}}');
            }} catch(e) {{}}

            if (collType) jsonObj.collection_type = collType;
            if (idsArray.length > 0) jsonObj.collection_ids = idsArray;
            else delete jsonObj.collection_ids;
            if (orderBy) jsonObj.order_by = orderBy;
            else delete jsonObj.order_by;

            document.getElementById('{name}_raw').value = JSON.stringify(jsonObj, null, 2);
        }}
        </script>
        """
        return mark_safe(html)


class BlockConfigAdminForm(forms.ModelForm):
    """Form customization for BlockConfig admin models."""

    class Meta:
        """Meta definitions for BlockConfigAdminForm."""

        model = BlockConfig
        fields = "__all__"
        widgets = {
            "extra_config": DynamicExtraConfigWidget(),
        }


@admin.register(BlockConfig)
class BlockConfigAdmin(admin.ModelAdmin):
    """Admin configuration for BlockConfig (block instances on pages)."""

    form = BlockConfigAdminForm
    list_display = ("order", "admin_name", "frontend_id", "is_active", "item_limit", "block_type")
    list_filter = ("is_active", "block_type")
    search_fields = ("admin_name", "frontend_id", "display_title")
    autocomplete_fields = []

    fieldsets = (
        (
            _("Identification"),
            {
                "fields": ("admin_name", "block_type", "frontend_id", "order", "is_active"),
                "description": _(
                    "ℹ️ Choose a Block Type (registered by the frontend) to know what "
                    "this block can display. The Frontend Identifier must match exactly."
                ),
            },
        ),
        (
            _("Personalization"),
            {
                "fields": ("display_title", "subtitle_or_text", "item_limit"),
            },
        ),
        (
            _("Theme (Colors)"),
            {
                "fields": ("background_color", "text_color"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Advanced & Visual Config"),
            {
                "fields": ("extra_config",),
                "description": _(
                    "Use the visual editor or the raw JSON textarea to configure this block's parameters."
                ),
            },
        ),
    )
