import json
from datetime import datetime, timezone
from types import SimpleNamespace

from src.narrative_envelope import (
    build_narrative_envelope,
)
from src.narrative_response import NarrativeResponse
from src.narrative_trace import (
    build_narrative_trace,
)


def make_evidence():
    return SimpleNamespace(
        evidence_id="evidence-test",
        pipeline_run_id="pipeline-test",
        source_table="project.dataset.table",
        object_uri="local://bucket/test.csv",
    )


def make_interaction():
    usage = SimpleNamespace(
        total_input_tokens=100,
        total_output_tokens=30,
        total_thought_tokens=200,
        total_tool_use_tokens=0,
        total_tokens=330,
    )

    steps = [
        SimpleNamespace(
            type="thought",
            content="private internal content",
        ),
        SimpleNamespace(
            type="model_output",
            content="final output",
        ),
    ]

    return SimpleNamespace(
        id="interaction-test",
        model="gemini-3.6-flash",
        created=datetime(
            2026,
            9,
            14,
            tzinfo=timezone.utc,
        ),
        status="completed",
        usage=usage,
        steps=steps,
    )


def make_narrative():
    return NarrativeResponse(
        status="answered",
        answer=(
            "قيمة Billed Cost أعلى من "
            "Effective Cost."
        ),
        used_metrics=[
            "billed_cost",
            "effective_cost",
        ],
        limitations=[
            "No utilization metrics are included.",
        ],
        unsupported_reason=None,
    )


def test_builds_backend_envelope():
    envelope = build_narrative_envelope(
        evidence=make_evidence(),
        interaction=make_interaction(),
        narrative=make_narrative(),
    )

    assert (
        envelope["provenance"]["evidence_id"]
        == "evidence-test"
    )
    assert (
        envelope["execution"]["interaction_id"]
        == "interaction-test"
    )
    assert (
        envelope["narrative"]["status"]
        == "answered"
    )

    # يثبت أن Envelope قابلة للتحويل إلى JSON.
    json.dumps(
        envelope,
        ensure_ascii=False,
    )


def test_envelope_does_not_store_full_objects():
    envelope = build_narrative_envelope(
        evidence=make_evidence(),
        interaction=make_interaction(),
        narrative=make_narrative(),
    )

    assert "evidence" not in envelope
    assert "interaction" not in envelope
    assert "usage" not in envelope["execution"]
    assert "steps" not in envelope["execution"]


def test_builds_safe_trace():
    trace = build_narrative_trace(
        interaction=make_interaction(),
        narrative=make_narrative(),
    )

    assert trace["interaction_id"] == (
        "interaction-test"
    )
    assert trace["narrative_status"] == "answered"
    assert trace["total_tokens"] == 330
    assert trace["step_types"] == [
        "thought",
        "model_output",
    ]


def test_trace_does_not_expose_thought_content():
    trace = build_narrative_trace(
        interaction=make_interaction(),
        narrative=make_narrative(),
    )

    serialized_trace = json.dumps(
        trace,
        ensure_ascii=False,
    )

    assert "private internal content" not in (
        serialized_trace
    )
    assert "signature" not in serialized_trace