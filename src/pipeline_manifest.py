# يحفظ السجل التشغيلي لتشغيل Pipeline واحد باسم run_id، ليبقى قابلاً للتتبع والتدقيق. ويعيد مسار الملف الناتج
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()

# احفظ Dictionary يمثل تشغيل Pipeline واحداً كملف JSON.
def write_pipeline_manifest(
    manifests_dir: Path,
    manifest: dict,
) -> Path:
    manifests_dir = Path(manifests_dir)

    manifests_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_path = (
        manifests_dir
        / f"{manifest['run_id']}.json"
    )

    manifest_path.write_text(
        # يجعل JSON مقروءاً ومنسقاً.
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return manifest_path