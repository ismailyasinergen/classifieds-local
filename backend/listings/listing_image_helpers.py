"""
SAVE_UPLOADED_LISTING_IMAGES_HELPER_EXTRACTION_V147
VALIDATE_UPLOADED_IMAGES_HELPER_EXTRACTION_V148

Listing image helper functions.

This module starts by housing save_uploaded_listing_images, which was previously
defined in backend/listings/views.py.

Import hygiene note:
Only imports required by listing image helpers should live here. UI and request
handling concerns stay in views.py.
"""

from __future__ import annotations

from .models import ListingImage
from pathlib import Path


def save_uploaded_listing_images(listing, uploaded_files):
    saved_count = 0

    for uploaded_file in uploaded_files:
        ListingImage.objects.create(
            listing=listing,
            image=uploaded_file,
        )
        saved_count += 1

    return saved_count


def validate_uploaded_images(uploaded_files):
    errors = []

    for uploaded_file in uploaded_files:
        extension = Path(uploaded_file.name).suffix.lower()
        content_type = uploaded_file.content_type

        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            errors.append(f"{uploaded_file.name}: unsupported file extension")
            continue

        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            errors.append(f"{uploaded_file.name}: unsupported file type")
            continue

        if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
            errors.append(f"{uploaded_file.name}: file is larger than {MAX_IMAGE_SIZE_MB} MB")

    return errors
