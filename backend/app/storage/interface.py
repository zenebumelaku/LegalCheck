from pathlib import Path
import os
import tempfile
from typing import Protocol


class PrivateFileStorage(Protocol):
    def store(self, key: str, content: bytes) -> None: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class LocalPrivateFileStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._root.chmod(0o700)

    def _path_for(self, key: str) -> Path:
        if not key or key != Path(key).name or "/" in key or "\\" in key or key.startswith("."):
            raise ValueError("Invalid private storage key.")
        path = (self._root / key).resolve()
        if path == self._root or self._root not in path.parents:
            raise ValueError("Invalid private storage key.")
        return path

    def store(self, key: str, content: bytes) -> None:
        path = self._path_for(key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=".upload-",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                os.chmod(temporary_path, 0o600)
                temporary_file.write(content)
            os.replace(temporary_path, path)
        except OSError:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

    def read(self, key: str) -> bytes:
        path = self._path_for(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        try:
            path.unlink()
        except FileNotFoundError:
            return
        parent = path.parent
        while parent != self._root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def get_private_storage(root: str) -> PrivateFileStorage:
    return LocalPrivateFileStorage(Path(root))
