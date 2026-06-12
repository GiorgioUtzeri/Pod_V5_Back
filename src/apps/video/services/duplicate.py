"""
Esup-Pod - Video duplication service.
"""

from django.db import transaction
from django.utils.text import slugify
from src.apps.video.models import Video
from .slug import generate_unique_slug
from .files import duplicate_source_file
from src.apps.video.services.sites import assign_default_site


@transaction.atomic
def duplicate_video(original: Video, user, request=None):
    """
    Duplicates a Video instance for the given user.

    Creates a new Video in DRAFT status with all scalar fields copied,
    the source file physically duplicated on disk, and all M2M relations
    (disciplines, restricted_groups, co_owners) mirrored.
    """

    base_slug = f"{original.slug}-copy"
    new_slug = generate_unique_slug(slugify(base_slug))

    duplicated = Video.objects.create(
        title=f"Copy of {original.title}",
        slug=new_slug,
        type=original.type,
        owner=user,
        description=original.description,
        is_auth_required=original.is_auth_required,
        password=original.password,
        allow_downloading=original.allow_downloading,
        is_360=original.is_360,
        transcript_language=original.transcript_language,
        license=original.license,
        cursus=original.cursus,
        language=original.language,
        thumbnail=original.thumbnail,
        status=Video.Status.DRAFT,
    )

    if original.sites.exists():
        duplicated.sites.set(original.sites.all())
    elif request:
        assign_default_site(duplicated, request)
    else:
        raise ValueError("Video must have at least one site")

    if original.video_file:
        duplicated.video_file.name = duplicate_source_file(
            duplicated.id,
            original.video_file.path,
            original.video_file.name,
        )
        duplicated.save(update_fields=["video_file"])

    duplicated.disciplines.set(original.disciplines.all())
    duplicated.restricted_groups.set(original.restricted_groups.all())
    duplicated.co_owners.set(original.co_owners.all())

    return duplicated
