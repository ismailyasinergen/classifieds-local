import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    """Local private volume; never supplies a publicly fetchable URL."""

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Private media has no public storage URL.")


def private_storage():
    return PrivateMediaStorage(file_permissions_mode=0o600, directory_permissions_mode=0o700)


def original_name(instance, filename):
    return f"originals/{instance.storage_key.hex}.bin"
