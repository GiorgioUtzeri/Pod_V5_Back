"""Esup-Pod - Migration command to import legacy WebTV data into Pod V5.

Usage examples:
    # Full migration (all steps)
    python manage.py Explosion

    # Dry-run (no writes — check counts and connectivity)
    python manage.py Explosion --dry-run

    # Migrate only the first 50 videos (smoke test)
    python manage.py Explosion --limit 50

    # Run only one specific step
    python manage.py Explosion --step videos
    python manage.py Explosion --step users
    python manage.py Explosion --step speakers
    python manage.py Explosion --step hyperlinks
    python manage.py Explosion --step documents
    python manage.py Explosion --step groupings
    python manage.py Explosion --step collections
    python manage.py Explosion --step comments

Prerequisites (run before the first migration):
    1. Create the webtv database:
       docker exec -i pod-db mysql -u root -proot_password \\
           -e "CREATE DATABASE IF NOT EXISTS webtv;"

    2. Import the dump:
       docker exec -i pod-db mysql -u root -proot_password webtv \\
           < dump-webtv-202510281226.sql

    3. Run all migration steps:
       docker compose -p esup-pod-back -f deployment/dev/docker-compose.yml \\
           exec api python manage.py Explosion

    4. Rebuild the search index after videos are migrated:
       docker compose -p esup-pod-back -f deployment/dev/docker-compose.yml \\
           exec api python manage.py reindex_videos
"""

import time

from django.core.management.base import BaseCommand
from django.db.models.signals import post_save, post_delete, pre_save

from src.apps.migration.utils.userMigrate import userMigrate
from src.apps.migration.utils.videoMigrate import videoMigrate
from src.apps.migration.utils.speakerMigrate import speakerMigrate
from src.apps.migration.utils.hyperlinkMigrate import hyperlinkMigrate
from src.apps.migration.utils.documentMigrate import documentMigrate
from src.apps.migration.utils.groupingMigrate import groupingMigrate
from src.apps.migration.utils.collectionMigrate import collectionMigrate
from src.apps.migration.utils.commentMigrate import commentMigrate

STEPS = {
    "users": userMigrate,
    "videos": videoMigrate,
    "speakers": speakerMigrate,
    "hyperlinks": hyperlinkMigrate,
    "documents": documentMigrate,
    "groupings": groupingMigrate,
    "collections": collectionMigrate,
    "comments": commentMigrate,
}

ALL_STEPS = list(STEPS.keys())


class Command(BaseCommand):
    """Migration command to import all legacy WebTV data into Pod V5."""

    help = (
        "Migrate legacy WebTV V4 data into Pod V5 (users, videos, speakers, collections…)"
    )

    def add_arguments(self, parser):
        """Define CLI arguments for the migration command."""
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit the number of videos to migrate (default: 0 = all). "
            "Useful for smoke testing: --limit 50",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Simulate the migration without writing anything to the database.",
        )
        parser.add_argument(
            "--step",
            type=str,
            default=None,
            choices=ALL_STEPS,
            help=f"Run only one specific migration step. Choices: {', '.join(ALL_STEPS)}",
        )

    def handle(self, *args, **kwargs):
        """Execute migration steps with signals disabled for bulk performance."""
        dry_run = kwargs.get("dry_run", False)
        step = kwargs.get("step")

        steps_to_run = [step] if step else ALL_STEPS

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "=" * 60 + "\n"
                    "  DRY-RUN MODE — aucune écriture en base de données\n"
                    "=" * 60
                )
            )

        self.stdout.write(f"Étapes à exécuter : {', '.join(steps_to_run)}\n")

        # Disable Django signals for the entire migration to avoid:
        # - Per-video cache flushes
        # - Per-video search index threads
        # - Per-video file duration extraction
        # - Per-video site assignment queries
        sep = "=" * 60
        with self._bypass_signals():
            start = time.time()

            for step_name in steps_to_run:
                self.stdout.write(
                    self.style.MIGRATE_HEADING(
                        f"\n{sep}\n  STEP: {step_name.upper()}\n{sep}"
                    )
                )
                step_start = time.time()
                STEPS[step_name](self, *args, **kwargs)
                elapsed = time.time() - step_start
                self.stdout.write(f"  ✓ {step_name} terminé en {elapsed:.1f}s\n")

            total_elapsed = time.time() - start
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{sep}\n"
                    f"  Migration complète en {total_elapsed:.1f}s\n"
                    f"{sep}"
                )
            )

        if not dry_run and "videos" in steps_to_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  N'oubliez pas de reconstruire l'index de recherche Redis :\n"
                    "   python manage.py reindex_videos\n"
                )
            )

    def _bypass_signals(self):
        """Context manager that disconnects Video-related signals during migration."""
        import contextlib

        @contextlib.contextmanager
        def _ctx():
            """Disconnect Video signals, yield, then reconnect them."""
            from src.apps.video.models import Video, Type, Subtitle
            from src.apps.video import signals as video_signals

            signals_to_pause = [
                (post_save, Video, video_signals.set_video_slug),
                (post_save, Video, video_signals.video_post_save),
                (post_save, Video, video_signals.auto_assign_site_to_video),
                (post_save, Video, video_signals.invalidate_cache_on_video_save),
                (post_delete, Video, video_signals.auto_delete_file_on_delete),
                (pre_save, Video, video_signals.auto_delete_file_on_change),
                (post_delete, Video, video_signals.invalidate_cache_on_video_delete),
                (
                    post_delete,
                    Subtitle,
                    video_signals.auto_delete_subtitle_file_on_delete,
                ),
                (post_save, Type, video_signals.auto_assign_site_to_type),
            ]

            self.stdout.write(
                "  [Signals] Désactivation des signaux Django pour la migration..."
            )
            disconnected = []
            for signal, sender, receiver_fn in signals_to_pause:
                if signal.disconnect(receiver_fn, sender=sender):
                    disconnected.append((signal, sender, receiver_fn))
            self.stdout.write(f"  [Signals] {len(disconnected)} signaux désactivés.")

            try:
                yield
            finally:
                self.stdout.write("  [Signals] Reconnexion des signaux Django...")
                for signal, sender, receiver_fn in disconnected:
                    signal.connect(receiver_fn, sender=sender, weak=False)
                self.stdout.write(f"  [Signals] {len(disconnected)} signaux reconnectés.")

        return _ctx()
