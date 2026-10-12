from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from PIL import Image
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings

from .helpers import MediaFixtures, image_upload


class MediaProcessingTests(MediaFixtures, TestCase):
    def test_processing_same_asset_twice_has_one_result(self):
        asset = self.attach()
        self.module("tasks").process_image(asset.pk)
        asset.refresh_from_db()
        first = asset.derivative.name
        self.module("tasks").process_image(asset.pk)
        asset.refresh_from_db()
        self.assertEqual(asset.state, "ready")
        self.assertEqual(asset.attempts, 1)
        self.assertEqual(asset.derivative.name, first)
        self.assertEqual(self.module("models").MediaAsset.objects.count(), 1)
        self.assertEqual(len(list(Path(self.directory.name).rglob("*.jpg"))), 1)

    def test_invalid_image_is_rejected(self):
        for content, mime in [(b"<svg></svg>", "image/svg+xml"), (b"not an image", "image/jpeg")]:
            with self.subTest(mime=mime), self.assertRaises(ValidationError):
                self.attach(uploaded_file=SimpleUploadedFile("image.jpg", content, content_type=mime))
        self.assertEqual(self.module("models").MediaAsset.objects.count(), 0)
        self.assertEqual(self.revision.images.count(), 0)
        self.assertEqual(list(Path(self.directory.name).rglob("*")), [])

    def test_corrupt_png_idat_crc_is_rejected_without_persistence(self):
        data = bytearray(image_upload(format="PNG").read())
        # Retain the real PNG header and compressed pixels; corrupt only IDAT's CRC.
        offset = 8
        while offset + 12 <= len(data):
            length = int.from_bytes(data[offset:offset + 4], "big")
            if data[offset + 4:offset + 8] == b"IDAT":
                data[offset + 8 + length] ^= 1
                break
            offset += 12 + length
        else:
            self.fail("Generated PNG must contain an IDAT chunk.")
        with self.assertRaises(ValidationError):
            self.attach(uploaded_file=SimpleUploadedFile(
                "corrupt.png", bytes(data), content_type="image/png"))
        self.assertEqual(self.module("models").MediaAsset.objects.count(), 0)
        self.assertEqual(self.revision.images.count(), 0)
        self.assertEqual(list(Path(self.directory.name).rglob("*")), [])

    def test_metadata_is_removed_from_derivative(self):
        asset = self.attach(uploaded_file=image_upload(metadata=True))
        self.module("tasks").process_image(asset.pk)
        asset.refresh_from_db()
        with asset.original.open("rb") as source, Image.open(source) as image:
            self.assertTrue(image.getexif())
        with asset.derivative.open("rb") as result, Image.open(result) as image:
            self.assertFalse(image.getexif())
            self.assertNotIn("exif", image.info)
            self.assertNotIn("icc_profile", image.info)
            self.assertEqual(image.format, "JPEG")

    def test_png_transparency_is_composited_on_white_in_decoded_derivative(self):
        cases = [("palette_index", "P", 0, (255, 255, 255)),
                 ("palette_alpha", "P", bytes([128, 255]), (255, 127, 127)),
                 ("rgb_color", "RGB", (255, 0, 0), (255, 255, 255)),
                 ("rgba_alpha", "RGBA", None, (255, 255, 255))]
        for name, mode, transparency, expected in cases:
            with self.subTest(representation=name):
                image = Image.new(mode, (64, 48), 0 if mode == "P" else
                                  ((255, 0, 0, 0) if mode == "RGBA" else (255, 0, 0)))
                try:
                    if mode == "P":
                        image.putpalette([255, 0, 0, 0, 0, 255] + [0] * 762)
                        image.paste(1, (32, 0, 64, 48))
                    else:
                        image.paste((0, 0, 255, 255) if mode == "RGBA" else (0, 0, 255),
                                    (32, 0, 64, 48))
                    encoded = BytesIO()
                    options = {} if transparency is None else {"transparency": transparency}
                    image.save(encoded, format="PNG", **options)
                finally:
                    image.close()
                asset = self.attach(uploaded_file=SimpleUploadedFile(
                    name + ".png", encoded.getvalue(), content_type="image/png"))
                with asset.original.open("rb") as original, Image.open(original) as source:
                    source.load()
                    self.assertEqual(source.mode, mode)
                    if transparency is not None:
                        self.assertIn("transparency", source.info)
                self.module("tasks").process_image(asset.pk)
                asset.refresh_from_db()
                self.assertEqual(asset.state, "ready")
                with asset.derivative.open("rb") as result, Image.open(result) as derivative:
                    derivative.load()
                    self.assertEqual(derivative.format, "JPEG")
                    self.assertEqual(derivative.size, (64, 48))
                    for actual, target in zip(derivative.getpixel((8, 24)), expected):
                        self.assertLessEqual(abs(actual - target), 8)
                    for actual, target in zip(derivative.getpixel((48, 24)), (0, 0, 255)):
                        self.assertLessEqual(abs(actual - target), 8)
                    self.assertFalse(derivative.getexif())
                    self.assertNotIn("transparency", derivative.info)

    def test_decoded_mime_must_match_claim(self):
        with self.assertRaises(ValidationError):
            self.attach(uploaded_file=image_upload(format="PNG", mime="image/jpeg"))

    def test_allowed_formats_decode_and_process(self):
        for format in ("JPEG", "PNG", "WEBP"):
            with self.subTest(format=format):
                asset = self.attach(uploaded_file=image_upload(format=format))
                self.module("tasks").process_image(asset.pk)
                asset.refresh_from_db()
                self.assertEqual(asset.state, "ready")
                self.assertEqual((asset.width, asset.height), (24, 18))

    @override_settings(MEDIA_MAX_UPLOAD_BYTES=100)
    def test_oversized_input_rejected_before_persistence(self):
        with self.assertRaises(ValidationError):
            self.attach()
        self.assertEqual(self.module("models").MediaAsset.objects.count(), 0)

    @override_settings(MEDIA_MAX_PIXELS=100)
    def test_pixel_limit_rejects_real_image(self):
        with self.assertRaises(ValidationError):
            self.attach(uploaded_file=image_upload(size=(11, 10)))

    def test_decompression_bomb_rejected(self):
        with patch.object(Image, "MAX_IMAGE_PIXELS", 100):
            with self.assertRaises(ValidationError):
                self.attach(uploaded_file=image_upload(size=(25, 20)))

    @override_settings(MEDIA_MAX_IMAGES_PER_REVISION=1)
    def test_file_count_bound_applies_to_upload_and_link(self):
        first = self.attach()
        another = self.draft()
        second = self.attach(another)
        with self.assertRaises(ValidationError):
            self.attach()
        with self.assertRaises(ValidationError):
            self.module("services").link_image(
                actor=self.owner, revision_id=self.revision.pk, asset_id=second.pk, position=1)
        self.assertEqual(self.revision.images.count(), 1)
        self.assertEqual(self.module("models").MediaAsset.objects.count(), 2)
        self.assertEqual(first.owner_id, self.owner.pk)

    def test_position_validation_and_duplicate_link(self):
        asset = self.attach()
        services = self.module("services")
        for position in (-1, True, "1"):
            with self.subTest(position=position), self.assertRaises(ValidationError):
                services.link_image(actor=self.owner, revision_id=self.revision.pk,
                                    asset_id=asset.pk, position=position)
        with self.assertRaises(ValidationError):
            services.link_image(actor=self.owner, revision_id=self.revision.pk,
                                asset_id=asset.pk, position=0)

    def test_server_names_prevent_filename_path_traversal(self):
        first, second = self.attach(), self.attach()
        self.assertNotEqual(first.original.name, second.original.name)
        self.assertNotIn("unsafe", first.original.name)
        self.assertNotIn("..", first.original.name)
        self.assertTrue(Path(first.original.path).is_relative_to(Path(self.directory.name)))

    def test_broker_failure_keeps_pending_upload_and_rescue_recovers(self):
        with patch("media.services.process_image.delay", side_effect=ConnectionError("broker unavailable")):
            with self.captureOnCommitCallbacks(execute=True):
                asset = self.attach()
        asset.refresh_from_db()
        self.assertEqual(asset.state, "pending")
        self.assertTrue(asset.original.storage.exists(asset.original.name))
        with patch("media.services.process_image.delay") as broker:
            self.module("tasks").rescue_pending_images()
            broker.assert_called_once_with(asset.pk)
        self.module("tasks").process_image(asset.pk)
        asset.refresh_from_db()
        self.assertEqual(asset.state, "ready")

    def test_enqueue_occurs_only_after_commit(self):
        with patch("media.services.process_image.delay") as broker:
            with self.captureOnCommitCallbacks(execute=True):
                asset = self.attach()
                broker.assert_not_called()
            broker.assert_called_once_with(asset.pk)

    def test_failure_retry_reuses_asset_and_has_bounded_attempts(self):
        asset = self.attach()
        original = asset.original.storage
        original.delete(asset.original.name)
        tasks = self.module("tasks")
        services = self.module("services")
        for attempt in range(1, 4):
            tasks.process_image(asset.pk)
            asset.refresh_from_db()
            self.assertEqual(asset.state, "failed")
            self.assertEqual(asset.attempts, attempt)
            self.assertEqual(asset.error_code, "processing_failed")
            if attempt < 3:
                services.retry_image(actor=self.owner, revision_id=self.revision.pk, asset_id=asset.pk)
        with self.assertRaises(ValidationError):
            services.retry_image(actor=self.owner, revision_id=self.revision.pk, asset_id=asset.pk)
        self.assertEqual(self.module("models").MediaAsset.objects.count(), 1)

    def test_retry_rejects_foreign_actor_and_wrong_revision(self):
        asset = self.attach()
        asset.original.storage.delete(asset.original.name)
        self.module("tasks").process_image(asset.pk)
        services = self.module("services")
        with self.assertRaises(PermissionDenied):
            services.retry_image(actor=self.other, revision_id=self.revision.pk, asset_id=asset.pk)
        with self.assertRaises(ValidationError):
            services.retry_image(actor=self.owner, revision_id=self.draft().pk, asset_id=asset.pk)

    def test_publication_inspects_actual_links_readiness_and_ownership(self):
        asset = self.attach()
        services = self.module("services")
        with self.assertRaises(ValidationError):
            services.require_revision_images_ready(revision=self.revision)
        self.module("tasks").process_image(asset.pk)
        services.require_revision_images_ready(revision=self.revision)
        self.module("models").MediaAsset.objects.filter(pk=asset.pk).update(owner=self.other)
        with self.assertRaises(ValidationError):
            services.require_revision_images_ready(revision=self.revision)


class MediaConcurrencyTests(MediaFixtures, TransactionTestCase):
    def test_concurrent_processing_has_one_derivative_and_attempt(self):
        self.assertEqual(connection.vendor, "postgresql")
        self.module("services")
        with patch("media.services.process_image.delay"):
            asset = self.attach()
        barrier = Barrier(2)

        def run():
            connections.close_all()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=5)
                self.module("tasks").process_image(asset.pk)
                return pid
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            pids = [future.result(timeout=15) for future in futures]
        self.assertEqual(len(set(pids)), 2)
        asset.refresh_from_db()
        self.assertEqual(asset.state, "ready")
        self.assertEqual(asset.attempts, 1)
        self.assertEqual(len(list(Path(self.directory.name).rglob("*.jpg"))), 1)
