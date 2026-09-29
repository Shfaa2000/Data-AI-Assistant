"""قواعد التحقق الأساسية لمسار البيانات."""

import math

import pandas as pd


REQUIRED_COLUMNS = {
    "AvailabilityZone",
    "BilledCost",
    "ChargeCategory",
    "ChargeDescription",
    "ChargeFrequency",
    "EffectiveCost",
    "ProviderName",
    "ServiceCategory",
    "ServiceName",
    "SubAccountName",
}


COST_COLUMNS = (
    "BilledCost",
    "EffectiveCost",
)


def validate_required_columns(
    data: pd.DataFrame,
) -> None:
    """التأكد من وجود الأعمدة التي يستخدمها المسار."""

    missing_columns = (
        REQUIRED_COLUMNS
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            f"{sorted(missing_columns)}"
        )


def validate_cost_columns(
    data: pd.DataFrame,
) -> None:
    """التأكد من أن أعمدة التكلفة رقمية ولا تحتوي Null."""

    for column in COST_COLUMNS:
        if not pd.api.types.is_numeric_dtype(
            data[column]
        ):
            raise ValueError(
                f"{column} must be numeric."
            )

        if data[column].isna().any():
            raise ValueError(
                f"{column} contains missing values."
            )


def validate_cleaning_result(
    source_data: pd.DataFrame,
    cleaned_data: pd.DataFrame,
) -> None:
    """التأكد أن التنظيف لم يحذف صفوفًا أو أعمدة أصلية."""

    if len(cleaned_data) != len(source_data):
        raise ValueError(
            "Cleaning changed the number of rows."
        )

    missing_source_columns = (
        set(source_data.columns)
        - set(cleaned_data.columns)
    )

    if missing_source_columns:
        raise ValueError(
            "Cleaning removed source columns: "
            f"{sorted(missing_source_columns)}"
        )


def validate_billed_cost_partitions(
    data: pd.DataFrame,
) -> None:
    """التأكد أن كل BilledCost سالبة أو صفرية أو موجبة."""

    negative_count = int(
        (data["BilledCost"] < 0).sum()
    )

    zero_count = int(
        (data["BilledCost"] == 0).sum()
    )

    positive_count = int(
        (data["BilledCost"] > 0).sum()
    )

    classified_rows = (
        negative_count
        + zero_count
        + positive_count
    )

    if classified_rows != len(data):
        raise ValueError(
            "Some BilledCost rows were not classified."
        )


def validate_provider_row_count(
    data: pd.DataFrame,
) -> None:
    """التأكد أن التجميع حسب Provider لم يفقد صفوفًا."""

    grouped_row_count = int(
        data.groupby(
            "ProviderName",
            dropna=False,
        )
        .size()
        .sum()
    )

    if grouped_row_count != len(data):
        raise ValueError(
            "Provider grouping changed the row count."
        )


def validate_provider_summary(
    data: pd.DataFrame,
    provider_summary: pd.DataFrame,
) -> None:
    """مطابقة عدد الصفوف ومجموع BilledCost مع البيانات."""

    summary_row_count = int(
        provider_summary["RowCount"].sum()
    )

    if summary_row_count != len(data):
        raise ValueError(
            "Provider Summary row count does not match."
        )

    summary_total = float(
        provider_summary[
            "TotalBilledCost"
        ].sum()
    )

    data_total = float(
        data["BilledCost"].sum()
    )

    if not math.isclose(
        summary_total,
        data_total,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Provider Summary billed cost does not match."
        )


def validate_analysis(
    data: pd.DataFrame,
    provider_summary: pd.DataFrame,
) -> None:
    """تشغيل قواعد التحقق النهائية للتحليل."""

    validate_cost_columns(data)
    validate_billed_cost_partitions(data)
    validate_provider_row_count(data)

    validate_provider_summary(
        data,
        provider_summary,
    )