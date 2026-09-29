"""حفظ تقرير منظم عن آخر تشغيل لمسار البيانات."""

import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def write_pipeline_manifest(
    output_file: Path,
    manifest: dict,
) -> Path:
    
    output_file = Path(output_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return output_file