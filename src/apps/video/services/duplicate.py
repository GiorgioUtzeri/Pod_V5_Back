from django.db import transaction
from django.utils.text import slugify

from src.apps.video.models import Video

from .slug import generate_unique_slug
from .files import duplicate_source_file


@transaction.atomic
def duplicate_video(original: Video, user):
    base_slug = slugify(f"{original.slug}-copy")
    new_slug = generate_unique_slug(base_slug)

    duplicated = Video.objects.create(
        title=f"Copy of {original.title}",
        video_file=original.video_file,
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

    # FILE COPY
    if original.video_file:
        duplicated.video_file.name = duplicate_source_file(
            duplicated.id,
            original.video_file.path,
            original.video_file.name,
        )
        duplicated.save(update_fields=["video_file"])

    # M2M
    duplicated.disciplines.set(original.disciplines.all())
    duplicated.restricted_groups.set(original.restricted_groups.all())
    duplicated.co_owners.set(original.co_owners.all())

    if original.channel:
        duplicated.channel = original.channel
        duplicated.save(update_fields=["channel"])

    return duplicated
