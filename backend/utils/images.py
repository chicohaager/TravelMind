"""
Shared image-processing utilities.

Single source of truth for validating, normalizing, compressing and extracting
metadata from uploaded images. Replaces the duplicated ``validate_*`` helpers and
raw ``f.write(contents)`` blocks in the diary / places / trips / avatar /
participants upload endpoints.

Pipeline per upload:
  1. Validate real MIME type (python-magic) against an allow-list.
  2. Guard against decompression-bomb images.
  3. Read EXIF metadata (capture timestamp + GPS) *before* re-encoding.
  4. Auto-orient via the EXIF orientation tag, then drop EXIF.
  5. Downscale to a web-friendly long edge and re-encode as WebP.
  6. Generate a small thumbnail for galleries.

Only Pillow + python-magic are required (both already in requirements.txt).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import magic
import structlog
from PIL import Image, ImageOps

logger = structlog.get_logger(__name__)

# Root that all served upload files live under; used to contain file deletions.
UPLOADS_ROOT = Path("./uploads").resolve()


def delete_upload_file(url: Optional[str]) -> None:
    """Delete an uploaded file by its public URL, contained within UPLOADS_ROOT.

    Safe against path traversal: the resolved target must stay inside the uploads
    root. Missing files and errors are swallowed (best-effort cleanup).
    """
    if not url or not url.startswith("/uploads/"):
        return
    try:
        relative = url[len("/uploads/"):]
        target = (UPLOADS_ROOT / relative).resolve()
        if not str(target).startswith(str(UPLOADS_ROOT)):
            logger.warning("upload_delete_path_escape_attempt", url=url)
            return
        if target.exists() and target.is_file():
            os.remove(target)
    except Exception as e:  # pragma: no cover - best-effort
        logger.warning("upload_file_delete_failed", url=url, error=str(e))

# Register the HEIC/HEIF decoder (default iPhone photo format) if available.
# Kept optional so the app still boots on environments that haven't installed
# the (libheif-backed) plugin yet.
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    _HEIF_SUPPORTED = True
except Exception:  # pragma: no cover - environment-dependent
    _HEIF_SUPPORTED = False
    logger.warning("pillow_heif_unavailable_heic_uploads_disabled")

# --- Configuration -----------------------------------------------------------

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}

if _HEIF_SUPPORTED:
    ALLOWED_EXTENSIONS |= {"heic", "heif"}
    ALLOWED_MIME_TYPES |= {"image/heic", "image/heif"}


def heic_supported() -> bool:
    """Whether HEIC/HEIF uploads can be decoded (pillow_heif is installed)."""
    return _HEIF_SUPPORTED

# Derivative sizes, measured on the long edge in pixels.
FULL_MAX_EDGE = 2560
THUMB_MAX_EDGE = 400

WEBP_QUALITY = 82
THUMB_QUALITY = 75

# Reject absurdly large images (decompression-bomb guard). 60 MP covers any
# real phone/camera photo while blocking crafted bombs.
MAX_PIXELS = 60_000_000

# EXIF tag IDs (avoids a dependency on ExifTags name maps).
_TAG_DATETIME = 0x0132          # DateTime (fallback)
_TAG_DATETIME_ORIGINAL = 0x9003  # DateTimeOriginal (preferred)
_IFD_EXIF = 0x8769               # Exif sub-IFD pointer
_IFD_GPS = 0x8825                # GPS sub-IFD pointer


@dataclass
class ProcessedImage:
    """Result of processing one uploaded image."""

    url: str                       # public URL of the web-sized image
    thumb_url: str                 # public URL of the thumbnail
    width: int
    height: int
    size_bytes: int
    taken_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def derive_thumb_url(url: str) -> str:
    """Derive the thumbnail URL for a stored image URL (WebP naming convention)."""
    if url and url.endswith(".webp"):
        return url[: -len(".webp")] + "_thumb.webp"
    return url


def validate_image(contents: bytes, filename: str) -> bool:
    """Validate an upload by extension *and* real content type."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    if ext not in ALLOWED_EXTENSIONS:
        return False
    try:
        mime_type = magic.Magic(mime=True).from_buffer(contents)
    except Exception:  # pragma: no cover - defensive
        return False
    return mime_type in ALLOWED_MIME_TYPES


def _gps_to_decimal(value, ref) -> Optional[float]:
    """Convert an EXIF ((deg),(min),(sec)) tuple + N/S/E/W ref to decimal degrees."""
    if not value or not ref:
        return None
    try:
        deg, minutes, seconds = value
        decimal = float(deg) + float(minutes) / 60 + float(seconds) / 3600
        if str(ref).upper() in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _extract_exif(img: Image.Image):
    """Best-effort extraction of (taken_at, latitude, longitude) from EXIF."""
    taken_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    try:
        exif = img.getexif()
        if not exif:
            return taken_at, latitude, longitude

        # DateTimeOriginal lives in the Exif sub-IFD; DateTime is a fallback.
        dt_raw = None
        try:
            dt_raw = exif.get_ifd(_IFD_EXIF).get(_TAG_DATETIME_ORIGINAL)
        except Exception:
            pass
        dt_raw = dt_raw or exif.get(_TAG_DATETIME)
        if dt_raw:
            try:
                taken_at = datetime.strptime(str(dt_raw), "%Y:%m:%d %H:%M:%S")
            except ValueError:
                taken_at = None

        try:
            gps = exif.get_ifd(_IFD_GPS)
        except Exception:
            gps = None
        if gps:
            # 1=LatRef, 2=Lat, 3=LngRef, 4=Lng
            latitude = _gps_to_decimal(gps.get(2), gps.get(1))
            longitude = _gps_to_decimal(gps.get(4), gps.get(3))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("exif_extract_failed", error=str(exc))
    return taken_at, latitude, longitude


def _resize(img: Image.Image, max_edge: int) -> Image.Image:
    """Return a copy scaled so its long edge is at most ``max_edge`` px."""
    width, height = img.size
    if max(width, height) <= max_edge:
        return img.copy()
    scale = max_edge / max(width, height)
    return img.resize((round(width * scale), round(height * scale)), Image.LANCZOS)


def process_and_save(
    contents: bytes,
    dest_dir: Path,
    url_prefix: str,
    *,
    make_thumb: bool = True,
    full_max_edge: int = FULL_MAX_EDGE,
) -> ProcessedImage:
    """
    Normalize, compress and persist an image, returning its public URLs and metadata.

    ``url_prefix`` is the public path the derivatives are served from, e.g.
    ``"/uploads/diary"``. Raises ``ValueError`` if the image cannot be decoded.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        img = Image.open(BytesIO(contents))
        img.load()
    except Exception as exc:
        raise ValueError(f"Could not decode image: {exc}") from exc

    width, height = img.size
    if width * height > MAX_PIXELS:
        raise ValueError("Image resolution too large")

    taken_at, latitude, longitude = _extract_exif(img)

    # Apply EXIF orientation, then flatten to a clean RGB(A) image (EXIF dropped).
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA") if img.mode in ("RGBA", "LA") else img.convert("RGB")

    stem = uuid.uuid4().hex
    full = _resize(img, full_max_edge)
    full_name = f"{stem}.webp"
    full_path = dest_dir / full_name
    full.save(full_path, "WEBP", quality=WEBP_QUALITY, method=6)

    thumb_url = f"{url_prefix}/{full_name}"
    if make_thumb:
        thumb = _resize(img, THUMB_MAX_EDGE)
        thumb_name = f"{stem}_thumb.webp"
        thumb.save(dest_dir / thumb_name, "WEBP", quality=THUMB_QUALITY, method=6)
        thumb_url = f"{url_prefix}/{thumb_name}"

    logger.info(
        "image_processed",
        full=full_name,
        out_size=full_path.stat().st_size,
        in_size=len(contents),
        width=full.width,
        height=full.height,
        has_gps=latitude is not None,
        has_date=taken_at is not None,
    )

    return ProcessedImage(
        url=f"{url_prefix}/{full_name}",
        thumb_url=thumb_url,
        width=full.width,
        height=full.height,
        size_bytes=full_path.stat().st_size,
        taken_at=taken_at,
        latitude=latitude,
        longitude=longitude,
    )
