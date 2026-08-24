"""
Esup-Pod - Celery tasks for the encoding app.

This module contains tasks for triggering and retrying encoding jobs.
"""

import logging
import json
import requests.exceptions

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.core.files.base import ContentFile
import os
from .conf import encoding_settings
from config.env import env

from src.apps.video.models import Video
from .services.runner_client import get_runner_client

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def trigger_runner_encoding_task(self, video_id: int, source_url: str):
    """
    Triggers an encoding task on the runner manager for a given video.
    Retries automatically on connection errors (up to max_retries times).
    """
    logger.info("Triggering encoding task for video %s", video_id)

    try:
        video = Video.objects.get(pk=video_id)
    except ObjectDoesNotExist:
        logger.error("Video %s not found. Aborting encoding task.", video_id)
        return None

    # Signal immediately that encoding has started.
    Video.objects.filter(pk=video_id).update(
        encoding_status=Video.EncodingStatus.PROCESSING
    )

    try:
        webhook_path = reverse("encoding:webhook")
        site_url = encoding_settings.site_url
        webhook_secret = env("ENCODING_WEBHOOK_SECRET", default="")
        notify_url = f"{site_url.rstrip('/')}{webhook_path}?secret={webhook_secret}&video_id={video_id}"

        rendition_config = {
            "360": {"resolution": "640x360", "encode_mp4": True},
            "720": {"resolution": "1280x720", "encode_mp4": True},
            "1080": {"resolution": "1920x1080", "encode_mp4": False},
        }

        from src.apps.video.conf import video_settings

        if getattr(video_settings, "use_hls", True):
            rendition_config["hls"] = {"encode_hls": True}

        parameters = {"rendition": json.dumps(rendition_config)}

        dressing = video.videos_dressing.first()
        if dressing:
            dressing_params = dressing.to_runner_parameters()
            for key in ["watermark", "opening_credits_video", "ending_credits_video"]:
                if key in dressing_params and dressing_params[key].startswith("/"):
                    dressing_params[key] = f"{site_url.rstrip('/')}{dressing_params[key]}"
            parameters["dressing"] = json.dumps(dressing_params)

        logger.debug("Sending notify_url=%s", notify_url)

        client = get_runner_client()
        response = client.execute_task(
            video_id=str(video.slug),
            source_url=source_url,
            notify_url=notify_url,
            parameters=parameters,
        )

        logger.info(
            "Runner manager accepted task for video %s. Response: %s",
            video_id,
            response,
        )
        return response

    except requests.exceptions.RequestException as exc:
        logger.warning(
            "Connection error while triggering encoding for video %s "
            "(attempt %s/%s): %s",
            video_id,
            self.request.retries + 1,
            self.max_retries,
            exc,
        )
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.error(
            "Unexpected error while triggering encoding for video %s: %s",
            video_id,
            exc,
            exc_info=True,
        )
        Video.objects.filter(pk=video_id).update(
            encoding_status=Video.EncodingStatus.ERROR
        )
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def download_runner_files_task(
    self, video_id: int, task_id: str, file_list: list, thumbnail_path: str
):
    """
    Asynchronously download encoded files (MP4 and HLS chunks) from the runner
    manager and process them. This prevents blocking the webhook.
    """
    logger.info("Starting async file download for video %s, task %s", video_id, task_id)
    try:
        video = Video.objects.get(pk=video_id)
    except ObjectDoesNotExist:
        logger.error("Video %s not found. Aborting download task.", video_id)
        return

    try:
        client = get_runner_client()
        from src.apps.encoding.models import EncodingVideo
        import contextlib

        if not encoding_settings.keep_source_file and video.video_file:
            video.video_file.delete(save=False)
            video.video_file = None

        hls_files = [
            f
            for f in file_list
            if f.endswith(".m3u8") or f.endswith(".ts") or f.endswith(".m4s")
        ]
        mp4_files = [f for f in file_list if f.endswith(".mp4")]

        # Process MP4s
        for file_name in mp4_files:
            res = file_name.split("_")[0] if "_" in file_name else file_name.split(".")[0]
            if not res.endswith("p"):
                res = f"{res}p"

            encoded_video_file = client.download_task_file_to_temp(task_id, file_name)
            encoding_obj, created = EncodingVideo.objects.get_or_create(
                video=video, resolution=res
            )
            if not created and encoding_obj.file:
                encoding_obj.file.delete(save=False)
            encoding_obj.file.save(encoded_video_file.name, encoded_video_file, save=True)
            with contextlib.suppress(FileNotFoundError):
                os.unlink(encoded_video_file.file.name)

        # Process HLS
        if hls_files:
            logger.info(
                "Found %d HLS files to download for video %s", len(hls_files), video_id
            )
            hls_dir = os.path.join(settings.MEDIA_ROOT, "video", "hls", str(video_id))
            os.makedirs(hls_dir, exist_ok=True)

            for file_name in hls_files:
                basename = os.path.basename(file_name)
                local_path = os.path.join(hls_dir, basename)

                endpoint = f"{client.url}/task/result/{task_id}/file/{file_name}"
                import requests

                with requests.get(
                    endpoint, headers=client.headers, stream=True, timeout=60
                ) as r:
                    r.raise_for_status()
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)

                # Register the master playlist in EncodingVideo
                if basename == "master.m3u8" or (
                    basename.endswith(".m3u8") and "master" in basename.lower()
                ):
                    relative_path = os.path.join("video", "hls", str(video_id), basename)
                    encoding_obj, created = EncodingVideo.objects.get_or_create(
                        video=video, resolution="hls"
                    )
                    if not created and encoding_obj.file:
                        encoding_obj.file.delete(save=False)
                    # We assign the name directly to avoid hashing, because HLS files must keep their original names
                    # to resolve relative paths to .ts chunks
                    encoding_obj.file.name = relative_path
                    encoding_obj.save(update_fields=["file"])

        # Thumbnail
        if thumbnail_path:
            if video.overview:
                video.overview.delete(save=False)
            new_overview = client.download_task_file_to_temp(task_id, thumbnail_path)
            video.overview.save(new_overview.name, new_overview, save=False)
            with contextlib.suppress(FileNotFoundError):
                os.unlink(new_overview.file.name)

        video.encoding_status = Video.EncodingStatus.DONE
        video.save(update_fields=["encoding_status"])
        logger.info("Async download completed successfully for video %s", video_id)

    except Exception as exc:
        logger.error(
            "Error downloading files for video %s: %s", video_id, exc, exc_info=True
        )
        video.encoding_status = Video.EncodingStatus.ERROR
        video.save(update_fields=["encoding_status"])
        raise self.retry(exc=exc)
