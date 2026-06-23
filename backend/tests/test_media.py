"""
Tests for the media lifecycle: upload -> derived photos -> caption -> gallery -> delete.

Exercises the cutover to the media table as the source of truth for diary photos,
plus the /api/media endpoints and trip-level access control.
"""

import io

import pytest
import pytest_asyncio
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from models.trip import Trip
from models.user import User


def _jpeg_bytes(color=(120, 160, 200), size=(800, 600)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def isolate_uploads(tmp_path, monkeypatch):
    """Redirect image writes/deletes into pytest's tmp dir so tests leave no artifacts."""
    import routes.diary as diary_routes
    import utils.images as images

    monkeypatch.setattr(diary_routes, "UPLOAD_DIR", tmp_path / "diary")
    monkeypatch.setattr(images, "UPLOADS_ROOT", tmp_path.resolve())


@pytest_asyncio.fixture
async def trip(db_session: AsyncSession, test_user: User) -> Trip:
    t = Trip(title="Lisbon", destination="Lisbon", owner_id=test_user.id)
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)
    return t


@pytest_asyncio.fixture
async def other_auth_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    user = User(
        username="mallory",
        email="mallory@example.com",
        hashed_password=User.hash_password("mallorypass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    resp = await client.post(
        "/api/auth/login",
        data={"username": "mallory", "password": "mallorypass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_entry(client, trip_id, headers) -> int:
    resp = await client.post(
        f"/api/diary/{trip_id}",
        json={"title": "Day 1", "content": "Arrived in Lisbon."},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_upload_creates_media_and_derives_photos(client, trip, auth_headers):
    entry_id = await _create_entry(client, trip.id, auth_headers)

    resp = await client.post(
        f"/api/diary/{entry_id}/upload-photo",
        files={"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["media"]["id"] > 0
    assert body["photo_url"].endswith(".webp")  # normalized to WebP
    assert body["thumb_url"].endswith("_thumb.webp")

    # The entry now exposes media[] and a derived, backward-compatible photos[].
    listing = await client.get(f"/api/diary/{trip.id}", headers=auth_headers)
    assert listing.status_code == 200
    entry = listing.json()[0]
    assert len(entry["media"]) == 1
    assert entry["photos"] == [entry["media"][0]["url"]]


@pytest.mark.asyncio
async def test_caption_update_and_gallery_and_delete(client, trip, auth_headers):
    entry_id = await _create_entry(client, trip.id, auth_headers)
    upload = await client.post(
        f"/api/diary/{entry_id}/upload-photo",
        files={"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=auth_headers,
    )
    media_id = upload.json()["media"]["id"]

    # Caption update
    patched = await client.patch(
        f"/api/media/{media_id}", json={"caption": "Sunset over Alfama"}, headers=auth_headers
    )
    assert patched.status_code == 200
    assert patched.json()["caption"] == "Sunset over Alfama"

    # Trip-wide gallery
    gallery = await client.get(f"/api/media/trip/{trip.id}", headers=auth_headers)
    assert gallery.status_code == 200
    items = gallery.json()
    assert [m["caption"] for m in items] == ["Sunset over Alfama"]
    # diary_entry_id is exposed so the map can filter to diary photos
    assert items[0]["diary_entry_id"] == entry_id
    assert items[0]["place_id"] is None

    # Delete
    deleted = await client.delete(f"/api/media/{media_id}", headers=auth_headers)
    assert deleted.status_code == 204

    empty = await client.get(f"/api/media/trip/{trip.id}", headers=auth_headers)
    assert empty.json() == []


@pytest.mark.asyncio
async def test_other_user_cannot_modify_media(client, trip, auth_headers, other_auth_headers):
    entry_id = await _create_entry(client, trip.id, auth_headers)
    upload = await client.post(
        f"/api/diary/{entry_id}/upload-photo",
        files={"file": ("photo.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=auth_headers,
    )
    media_id = upload.json()["media"]["id"]

    patched = await client.patch(
        f"/api/media/{media_id}", json={"caption": "hijack"}, headers=other_auth_headers
    )
    assert patched.status_code in (403, 404)

    deleted = await client.delete(f"/api/media/{media_id}", headers=other_auth_headers)
    assert deleted.status_code in (403, 404)
