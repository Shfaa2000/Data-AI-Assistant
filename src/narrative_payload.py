"""قراءة أحدث Evidence موثقة واستخراج Payload مالية صغيرة لخدمة واحدة."""

from pathlib import Path

from src.config import LATEST_EVIDENCE_FILE
from src.evidence import EvidenceBundle

# مسار ملف → قراءة JSON → EvidenceBundle → تحقق VERIFIED
def load_verified_evidence(
    evidence_path: Path = LATEST_EVIDENCE_FILE,
) -> EvidenceBundle:
    """قراءة Evidence والتحقق من بنيتها وحالتها."""

    if not evidence_path.is_file():
        raise FileNotFoundError(
            f"Evidence file not found: {evidence_path}"
        )

    evidence_json = evidence_path.read_text(
        encoding="utf-8"
    )

    evidence = EvidenceBundle.model_validate_json(
        evidence_json
    )

    if evidence.status != "VERIFIED":
        raise ValueError(
            "Evidence is not verified: "
            f"{evidence.evidence_id}"
        )

    return evidence

# EvidenceBundle → Service Breakdown → تحقق الحقول → Payload
def build_service_narrative_payload(
    evidence: EvidenceBundle,
) -> dict:
    """استخراج أصغر Payload مالية لازمة لسرد خدمة واحدة."""

    if evidence.status != "VERIFIED":
        raise ValueError(
            "Narrative payload requires verified evidence."
        )

    breakdown = evidence.service_breakdown
    top_service = evidence.top_service

    if not isinstance(breakdown, dict):
        raise ValueError(
            "Evidence contains no service breakdown."
        )

    if not isinstance(top_service, dict):
        raise ValueError(
            "Evidence contains no top service."
        )

    if breakdown.get("status") != "ok":
        raise ValueError(
            "Service breakdown status is not ok."
        )

    required_identity_fields = (
        "provider",
        "service",
        "currency",
    )

    missing_identity_fields = [
        field
        for field in required_identity_fields
        if not breakdown.get(field)
    ]

    if missing_identity_fields:
        raise ValueError(
            "Service breakdown is missing fields: "
            f"{missing_identity_fields}"
        )

    totals = breakdown.get("totals")

    if not isinstance(totals, dict):
        raise ValueError(
            "Service breakdown contains no totals."
        )

    required_metric_fields = (
        "billed_cost",
        "effective_cost",
        "negative_billed_cost",
    )

    missing_metric_fields = [
        field
        for field in required_metric_fields
        if field not in totals
        or totals[field] is None
    ]

    if missing_metric_fields:
        raise ValueError(
            "Service breakdown totals are missing fields: "
            f"{missing_metric_fields}"
        )

    top_service_identity = {
        "provider": top_service.get("ProviderName"),
        "service": top_service.get("ServiceName"),
        "currency": top_service.get("BillingCurrency"),
    }

    breakdown_identity = {
        "provider": breakdown["provider"],
        "service": breakdown["service"],
        "currency": breakdown["currency"],
    }

    if top_service_identity != breakdown_identity:
        raise ValueError(
            "Top service identity does not match "
            "service breakdown identity."
        )

    if not evidence.limitations:
        raise ValueError(
            "Evidence contains no limitations."
        )

    return {
        "provider": breakdown["provider"],
        "service": breakdown["service"],
        "currency": breakdown["currency"],
        "billed_cost": totals["billed_cost"],
        "effective_cost": totals["effective_cost"],
        "negative_billed_cost": (
            totals["negative_billed_cost"]
        ),
        "limitations": list(evidence.limitations),
    }