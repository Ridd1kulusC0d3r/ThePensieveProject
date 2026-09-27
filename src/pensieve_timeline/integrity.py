"""Evidence hashing without modifying the input."""

from pathlib import Path
import hashlib

CHUNK_SIZE = 1024 * 1024

def fingerprint(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"entrada não é arquivo regular: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
    return {"algorithm": "sha256", "digest": digest.hexdigest(), "size_bytes": size, "path": str(path)}
