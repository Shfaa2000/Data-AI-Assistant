# يعرّف واجهة FastAPI التي تستقبل طلبات FinOps، تتحقق من مدخلاتها، وتربطها بتوابع تحليل BigQuery.
import logging
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError
from google.cloud import bigquery
from pydantic import ValidationError

from run_finops_analytics import read_service_costs
from src.config import (
    BQ_DATASET_ID,
    GCP_PROJECT_ID,
    LATEST_EVIDENCE_FILE,
)
from src.evidence import EvidenceBundle
from src.service_breakdown import read_service_breakdown



app = FastAPI(
    title="Data-AI Assistant",
    version="0.1.0",
)

#     logger باسم الملف الحالي حتى تسجل الأخطاء مع مصدرها. تركيب قياسي.
logger = logging.getLogger(__name__)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "scope": "api_process_only",
    }


@app.get(
    "/finops/evidence/latest",
    response_model=EvidenceBundle,
)
def latest_finops_evidence():
    """Return the latest verified evidence without rerunning SQL."""

    if not LATEST_EVIDENCE_FILE.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "No verified evidence exists. "
                "Run run_finops_evidence.py first."
            ),
        )

    try:
        json_content = LATEST_EVIDENCE_FILE.read_text(
            encoding="utf-8"
        )
        return EvidenceBundle.model_validate_json(json_content)

    except (OSError, ValidationError) as exc:
        logger.exception("Latest evidence is unreadable or invalid")
        raise HTTPException(
            status_code=500,
            detail="Latest evidence failed contract validation.",
        ) from exc


#      يسجل endpoint خاصة بترتيب الخدمات.
@app.get("/finops/services")
def service_costs(
    #     قواعد validation ووصف للمدخلات يظهران أيضًا داخل Swagger. الصياغة قياسية، لكن يجب فهم الحدود.
    currency: Annotated[
        str,
        Query(
            min_length=3,
            max_length=3,
            pattern="^[A-Za-z]{3}$",
        ),
    ] = "USD",
    provider: Annotated[
        str,
        Query(max_length=100),
    ] = "",
    top: Annotated[
        int,
        Query(ge=1, le=50),
    ] = 5,
):
    client = None

    try:
        client = bigquery.Client(project=GCP_PROJECT_ID)

        dataset = client.get_dataset(
            f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
        )
        #    هنا تنتقل المسؤولية من طبقة HTTP إلى منطق التحليل. API لا تعيد كتابة الاستعلام.
        return read_service_costs(
            client=client,
            location=dataset.location,
            currency=currency.upper(),
            provider=provider.strip(),
            top_n=top,
        )

    except GoogleAuthError as exc:
        logger.exception("Google authentication failed")
        raise HTTPException(
            status_code=503,
            detail="Google authentication failed. Check the server terminal.",
        ) from exc

    except GoogleAPICallError as exc:
        logger.exception("BigQuery request failed")
        raise HTTPException(
            status_code=502,
            detail="BigQuery request failed. Check the server terminal.",
        ) from exc

    finally:
        if client is not None:
            client.close()

#     يسلك الهيكل نفسه، لكنه يطلب provider وservice ويستدعي read_service_breakdown بدل read_service_costs.
@app.get("/finops/service-breakdown")
def service_breakdown(
    provider: Annotated[
        str, Query(min_length=1, max_length=100, pattern=r"\S")
    ],
    service: Annotated[
        str, Query(min_length=1, max_length=200, pattern=r"\S")
    ],
    currency: Annotated[
        str, Query(pattern="^[A-Za-z]{3}$")
    ] = "USD",
):
    client = None

    try:
        client = bigquery.Client(project=GCP_PROJECT_ID)
        dataset = client.get_dataset(
            f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
        )

        return read_service_breakdown(
            client=client,
            location=dataset.location,
            provider=provider.strip(),
            service=service.strip(),
            currency=currency.upper(),
        )

    except GoogleAuthError as exc:
        logger.exception("Google authentication failed")
        raise HTTPException(
            status_code=503,
            detail="Google authentication failed.",
        ) from exc

    except GoogleAPICallError as exc:
        logger.exception("BigQuery request failed")
        raise HTTPException(
            status_code=502,
            detail="BigQuery request failed.",
        ) from exc

    finally:
        if client is not None:
            client.close()