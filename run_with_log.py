#غلاف تشغيل يشغّل run_cloud_pipeline.py في عملية منفصلة ويحفظ جميع مخرجاتها في Log وملخص JSON.

# وظيفتها قراءة خيارات المستخدم من Terminal.
import argparse
import json
import os
#وظيفتها تشغيل برنامج أو ملف آخر كعملية مستقلة.
import subprocess
import sys
from datetime import datetime, timezone
#تنشئ معرفًا شبه فريد وعشوائيًا.
from uuid import uuid4

from src.config import BASE_DIR


def main():
    #    يمنع تشغيل --local-only و--test-failure معًا. تركيب قياسي، لكن افهمي سبب التعارض.
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--local-only", action="store_true")
    modes.add_argument("--test-failure", action="store_true")
    args = parser.parse_args()

    #    يعطي كل تشغيل هوية فريدة قابلة للربط بين Log وSummary. تفاصيل UUID والتنسيق قياسية.
    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    log_dir = BASE_DIR / "reports" / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.log"
    summary_path = log_dir / f"{run_id}.json"

    if args.test_failure:
        mode = "logging_failure_test"
        command = [
            sys.executable,
            "-c",
            "raise RuntimeError('Intentional logging test')",
        ]
    else:
        mode = "local_only" if args.local_only else "full_pipeline"
        command = [sys.executable, "-u", "run_cloud_pipeline.py"]
        if args.local_only:
            command.append("--local-only")

    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    print(f"RUN_ID: {run_id}", flush=True)
    print(f"LOG: {log_path}", flush=True)

    with log_path.open("x", encoding="utf-8") as log:
        try:
            result = subprocess.run(
                command,
                cwd=BASE_DIR,
                env=environment,
                stdout=log,
                #يشغّل الـPipeline كعملية منفصلة. stdout وstderr يذهبان إلى Log، وcheck=False يسمح للغلاف بتسجيل نتيجة الفشل بدل أن يتوقف قبل كتابة Summary.
                stderr=subprocess.STDOUT,
                check=False,
            )
            exit_code = result.returncode
        except OSError as error:
            log.write(f"Could not start process: {error}\n")
            exit_code = 1

    finished = datetime.now(timezone.utc)
    summary = {
        "run_id": run_id,
        "mode": mode,
        "status": "SUCCESS" if exit_code == 0 else "FAILED",
        "exit_code": exit_code,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "log_file": log_path.name,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"STATUS: {summary['status']}")
    print(f"SUMMARY: {summary_path}")
    return exit_code


if __name__ == "__main__":
    #    يخرج من الملف بنفس Exit Code الخاص بالـPipeline، حتى تستطيع أدوات أخرى معرفة النجاح أو الفشل.
    raise SystemExit(main())