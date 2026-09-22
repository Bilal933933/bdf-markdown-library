"""Local filesystem storage — implements Storage, knows no domain concepts.

Required: base_dir. Optional: none.
Writes are atomic (temp file + rename) so crashed workers never leave halves.
"""

import os
import tempfile
from pathlib import Path


class LocalStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def _resolve(self, key: str) -> Path:
        candidate = Path(key)
        if not key or key.startswith("/") or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"unsafe storage key: {key!r}")
        return self.base_dir / key

    def save(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
        try:
            with os.fdopen(handle, "wb") as file:
                file.write(data)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return key

    def load(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise FileNotFoundError(f"storage key not found: {key!r}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()
