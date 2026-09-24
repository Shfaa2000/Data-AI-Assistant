import math
import pandas as pd

REQUIRED_COLUMNS = {
    "ProviderName",
    "ServiceName",
    "ServiceCategory",
    "ChargeCategory",
    "BilledCost",
    "EffectiveCost",
}

def validate_required_columns(data: pd.DataFrame) -> None:
    missing_columns = (REQUIRED_COLUMNS - set(data.columns))

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing_columns)}"
        )


def validate_billed_cost_partitions(data: pd.DataFrame) -> None:
    missing_count = (
        data["BilledCost"]
        .isna()
        .sum()
    )

    assert missing_count == 0, (
        "BilledCost contains missing values."
    )

    negative_count = (data["BilledCost"] < 0).sum()

    zero_count = (data["BilledCost"] == 0).sum()

    positive_count = (data["BilledCost"] > 0).sum()

    assert (
        negative_count
        + zero_count
        + positive_count
        == len(data)
    )


def validate_provider_row_count(data: pd.DataFrame) -> None:
    provider_row_count = (
        data.groupby(
            "ProviderName",
            dropna=False
        )
        .size()
        .sum()
    )

    assert provider_row_count == len(data)


def validate_provider_summary(data: pd.DataFrame,provider_summary: pd.DataFrame) -> None:
    assert (
        provider_summary["RowCount"].sum()== len(data))

    provider_total = (provider_summary["TotalBilledCost"].sum())

    raw_total = (data["BilledCost"].sum())

    assert math.isclose(
        provider_total,
        raw_total,
        rel_tol=1e-9
    )


def validate_analysis(data: pd.DataFrame,provider_summary: pd.DataFrame) -> None:

    validate_billed_cost_partitions(data)

    validate_provider_row_count(data)

    validate_provider_summary(data,provider_summary)