from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


def decode_image(data):
    """Fully decode the first frame, with bounded dimensions and bomb warnings fatal."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as probe:
                format = probe.format
                width, height = probe.size
                if format not in ALLOWED_MIME or width < 1 or height < 1:
                    raise ValidationError("Yalnız JPEG, PNG veya WebP görselleri yükleyin.")
                if width * height > settings.MEDIA_MAX_PIXELS:
                    raise ValidationError("Görsel piksel sınırını aşıyor.")
                probe.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()
                return image.copy(), format, width, height
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValidationError("Görsel dosyası geçersiz veya güvenli değil.") from exc


def validate_upload(uploaded_file):
    maximum = settings.MEDIA_MAX_UPLOAD_BYTES
    if getattr(uploaded_file, "size", 0) > maximum:
        raise ValidationError("Görsel dosya boyutu sınırını aşıyor.")
    # Read at most one byte beyond the limit, independent of caller's reported size.
    uploaded_file.seek(0)
    data = uploaded_file.read(maximum + 1)
    if not data or len(data) > maximum:
        raise ValidationError("Görsel dosya boyutu geçersiz.")
    image, format, width, height = decode_image(data)
    image.close()
    mime = ALLOWED_MIME[format]
    if getattr(uploaded_file, "content_type", None) != mime:
        raise ValidationError("Dosya türü görsel içeriğiyle eşleşmiyor.")
    return data, mime, width, height
