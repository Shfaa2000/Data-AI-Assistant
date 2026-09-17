# يتحقق حتميًا من أن الأرقام المالية في Narrative
# مأخوذة من الـPayload الموثقة ولم يولدها النموذج.

from decimal import Decimal
import re

from matplotlib import text
from src.narrative_response import NarrativeResponse

NUMBER_PATTERN = re.compile(
    r"(?<![\w.])[+-]?\d+(?:\.\d+)?(?![\w.])"
)

class NarrativeGroundingError(ValueError):
    """يُرفع عندما يحتوي الجواب ادعاءً ماليًا غير موثق."""



def extract_decimal_values(
    text: str,
) -> list[Decimal]:
    """استخراج الأرقام المستقلة من النص."""
    decimal_values = []
    for match in NUMBER_PATTERN.finditer(text):
        decimal_value = Decimal(
            match.group(0)
        )
        decimal_values.append(decimal_value)

    return decimal_values


def validate_narrative_grounding(
    payload: dict,
    narrative: NarrativeResponse,
) -> None:
    """التحقق من تطابق أرقام Narrative مع Payload."""
    metric_names = narrative.used_metrics
    answer_values = extract_decimal_values(
        narrative.answer
    )
    if narrative.status == "unsupported":
        if metric_names:
            raise NarrativeGroundingError(
                "Unsupported narrative must not "
                "include used metrics."
            )

        if answer_values:
            raise NarrativeGroundingError(
                "Unsupported narrative contains "
                "an unapproved numeric value."
            )

    allowed_values = {}
    for(metric_name) in metric_names:
        if metric_name not in payload:
            raise NarrativeGroundingError(
                f"Metric '{metric_name}' is not "
                "present in the payload."
            )
        allowed_values[metric_name] = Decimal(str(payload[metric_name]))

    expected_values = set(
        allowed_values.values()
    )
    actual_values = set(answer_values)

    missing_values = (
    expected_values - actual_values
    )

    unexpected_values = (
        actual_values - expected_values
    )

    if missing_values:
        raise NarrativeGroundingError(
            "Narrative omitted one or more "
            "declared metric values."
        )

    if unexpected_values:
        raise NarrativeGroundingError(
            "Narrative contains numeric values "
            "not supplied by the payload."
    )

    return