import importlib
import importlib.util
from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from accounts.models import User
from catalog.models import AttributeSchema, Category
from listings.services import create_listing_draft


def image_upload(*, size=(24, 18), format="JPEG", mime=None, metadata=False):
    output = BytesIO()
    image = Image.new("RGB", size, "orange")
    options = {}
    if metadata and format == "JPEG":
        exif = Image.Exif()
        exif[270] = "private camera metadata"
        exif[34853] = {1: "N", 2: (1.0, 2.0, 3.0)}
        options["exif"] = exif
    image.save(output, format=format, **options)
    return SimpleUploadedFile("../../unsafe.php", output.getvalue(),
                              content_type=mime or Image.MIME[format])


class MediaFixtures:
    def setUp(self):
        super().setUp()
        self.directory = TemporaryDirectory(prefix="classifieds-media-test-")
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(PRIVATE_MEDIA_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.owner = User.objects.create_user("media-owner@example.test", "password")
        self.other = User.objects.create_user("media-other@example.test", "password")
        self.category = Category.objects.create(name="Fotoğraf", slug="media")
        self.schema = AttributeSchema.objects.create(
            category=self.category, version=1, definition={"fields": {}})
        self.revision = self.draft()

    def module(self, name):
        self.assertIsNotNone(importlib.util.find_spec("media." + name),
                             "Task3 private media behavior has not been implemented")
        return importlib.import_module("media." + name)

    def draft(self, actor=None):
        return create_listing_draft(actor=actor or self.owner,
                                    category_id=self.category.pk, content={})

    def attach(self, revision=None, uploaded_file=None):
        return self.module("services").attach_image(
            actor=self.owner, revision_id=(revision or self.revision).pk,
            uploaded_file=uploaded_file or image_upload())
