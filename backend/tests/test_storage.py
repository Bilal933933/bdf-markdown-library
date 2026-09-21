from pathlib import Path

import pytest

from app.infrastructure.storage import LocalStorage


def test_roundtrip(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    assert storage.save("a/b.bin", b"\x00\x01") == "a/b.bin"
    assert storage.exists("a/b.bin") is True
    assert storage.load("a/b.bin") == b"\x00\x01"


def test_missing_key(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    assert storage.exists("nope") is False
    with pytest.raises(FileNotFoundError):
        storage.load("nope")
    storage.delete("nope")


def test_delete_removes(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.save("x", b"data")
    storage.delete("x")
    assert storage.exists("x") is False


def test_overwrite_replaces(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    storage.save("x", b"old")
    storage.save("x", b"new")
    assert storage.load("x") == b"new"


def test_unsafe_keys_rejected(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)
    for key in ("", "/abs", "../escape", "a/../../escape"):
        with pytest.raises(ValueError):
            storage.save(key, b"data")


def test_default_storage_dir_is_configured() -> None:
    from app.core.config import Settings

    assert Settings().storage_dir.name == "storage"
