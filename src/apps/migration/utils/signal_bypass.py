"""Esup-Pod - Utility context manager to bypass Django signals during migration.

During a bulk migration, every Video.save() triggers multiple signals:
  - video_post_save         → tries to read duration from a file that doesn't exist
  - auto_assign_site        → one extra SQL query per video
  - invalidate_cache        → flushes Redis on every single save
  - search auto-index       → spawns a daemon thread per video, all fail

This module is kept for reference. The active bypass logic lives directly
in the Explosion management command for simplicity and reliability.
"""

# noqa: F401 - module intentionally kept minimal
