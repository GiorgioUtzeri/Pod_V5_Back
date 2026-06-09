import shutil
import os


def duplicate_source_file(video_id, src_path, original_name):
    """
    Physically duplicates a video file on disk.
    """

    base_dir = os.path.dirname(src_path)
    filename = os.path.basename(src_path)

    new_filename = f"{video_id}_{filename}"
    new_path = os.path.join(base_dir, new_filename)

    shutil.copy2(src_path, new_path)

    return new_path
