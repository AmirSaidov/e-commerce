from django.core.files.storage import default_storage


def absolute_media_url(request, file_or_name):
    """Абсолютный URL файла: фронт и API живут на разных доменах.

    Если хранилище само отдаёт абсолютный URL (Cloudinary, R2), build_absolute_uri его не меняет.
    """
    name = getattr(file_or_name, "name", file_or_name)
    if not name:
        return None
    url = default_storage.url(name)
    return request.build_absolute_uri(url) if request is not None else url
