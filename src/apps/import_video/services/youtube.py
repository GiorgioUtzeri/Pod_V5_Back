"""
Esup-Pod - YouTube import service.
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_youtube_metadata(source_url: str) -> dict:
    """
    Fetches metadata from a YouTube video URL.
    Returns a dict with title, publish_date, and stream object.
    Raises ValueError on failure.
    """
    try:
        from pytubefix import YouTube

        yt = YouTube(source_url, "WEB")
        stream = yt.streams.get_highest_resolution()

        if not stream:
            raise ValueError("No downloadable stream found for this YouTube video.")

        return {
            "title": yt.title,
            "publish_date": yt.publish_date,
            "stream": stream,
            "filesize": stream.filesize,
        }

    except ImportError:
        raise ValueError("pytubefix is not installed. Cannot import YouTube videos.")
    except Exception as e:
        raise ValueError(f"Failed to fetch YouTube metadata: {e}")


def download_youtube_video(source_url: str, dest_dir: str) -> str:
    """
    Downloads a YouTube video to the given directory.
    Returns the path of the downloaded file.
    Raises ValueError on failure.
    """
    from src.apps.import_video.services.downloader import check_video_size

    metadata = get_youtube_metadata(source_url)
    check_video_size(metadata["filesize"])

    try:
        stream = metadata["stream"]
        os.makedirs(dest_dir, exist_ok=True)
        path = stream.download(output_path=dest_dir)
        logger.info("YouTube video downloaded to %s", path)
        return path

    except Exception as e:
        raise ValueError(f"Failed to download YouTube video: {e}")
