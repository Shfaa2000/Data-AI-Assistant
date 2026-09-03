# يحسب بصمة الملف، يبني عنوان Object، ثم يخزنه مرة واحدة أو يعيد استخدامه.

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


CHUNK_SIZE = 1024 * 1024


def calculate_file_sha256(
    file_path: Path,
) -> str:
    digest = hashlib.sha256()

    with Path(file_path).open("rb") as file:
        for chunk in iter(
            lambda: file.read(CHUNK_SIZE),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def build_object_name(
    file_hash: str,
    prefix: str,
) -> str:
    clean_prefix = prefix.strip("/")

    return (
        f"{clean_prefix}/"
        f"sha256={file_hash}/"
        "billing_cleaned.csv"
    )


def store_or_reuse_local_object(
    source_path: Path,
    storage_root: Path,
    bucket_name: str,
    object_name: str,
    expected_sha256: str,
) -> dict:
    source_path = Path(source_path)
    object_path = PurePosixPath(object_name)

    if object_path.is_absolute() or ".." in object_path.parts:
        raise ValueError(
            f"Unsafe object name: {object_name}"
        )

    destination = (
        Path(storage_root)
        / bucket_name
        / Path(*object_path.parts)
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    reused = destination.exists()

    if not reused:
        shutil.copy2(
            source_path,
            destination,
        )

    actual_sha256 = calculate_file_sha256(
        destination
    )

    if actual_sha256 != expected_sha256:
        raise ValueError(
            "Stored object hash does not match "
            "the source file hash."
        )

    file_stat = destination.stat()

    return {
        "backend": "local",
        "bucket": bucket_name,
        "object_name": object_name,
        "uri": (
            f"local://{bucket_name}/"
            f"{object_name}"
        ),
        "local_path": str(
            destination.resolve()
        ),
        "size_bytes": file_stat.st_size,
        "sha256": actual_sha256,
        "stored": not reused,
        "reused": reused,
        "modified_at_utc": (
            datetime.fromtimestamp(
                file_stat.st_mtime,
                timezone.utc,
            ).isoformat()
        ),
    }