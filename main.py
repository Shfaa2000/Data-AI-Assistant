"""تشغيل مسار البيانات المحلي من CSV إلى Cleaned CSV."""

import pandas as pd

from src.analytics import (
    get_analysis_results,
)
from src.cleaning import (
    clean_billing_data,
)
from src.config import (
    BILLING_FILE,
    CLEANED_BILLING_FILE,
)
from src.ingestion import (
    load_data,
)
from src.investigations import (
    investigate_billed_cost_outliers,
    investigate_billed_cost_outliers_by_service,
)
from src.profiling import (
    profile_data,
)
from src.validation import (
    validate_analysis,
    validate_cleaning_result,
    validate_required_columns,
)


def print_section(
    title: str,
) -> None:
    """طباعة عنوان واضح لكل مرحلة."""

    print(
        f"\n{'=' * 70}"
    )

    print(title)

    print(
        f"{'=' * 70}"
    )


def run_data_pipeline() -> pd.DataFrame:
    """تشغيل مسار البيانات المحلي وإعادة البيانات المنظفة."""

    print_section(
        "1. LOAD RAW DATA"
    )

    data = load_data(
        BILLING_FILE
    )

    print(
        f"Loaded rows: {len(data)}"
    )

    print(
        f"Loaded columns: {len(data.columns)}"
    )

    print_section(
        "2. VALIDATE INPUT DATA"
    )

    validate_required_columns(
        data
    )

    print(
        "Required columns validation: PASS"
    )

    print_section(
        "3. PROFILE RAW DATA"
    )

    profile_data(
        data
    )

    print_section(
        "4. CLEAN DATA"
    )

    clean_data = clean_billing_data(
        data
    )

    validate_cleaning_result(
        source_data=data,
        cleaned_data=clean_data,
    )

    added_columns = [
        column
        for column in clean_data.columns
        if column not in data.columns
    ]

    print(
        "Cleaning validation: PASS"
    )

    print(
        f"Added columns: {added_columns}"
    )

    print_section(
        "5. ANALYZE AND VALIDATE DATA"
    )

    analysis_results = (
        get_analysis_results(
            clean_data
        )
    )

    provider_summary = (
        analysis_results[
            "Provider Summary"
        ]
    )

    validate_analysis(
        data=clean_data,
        provider_summary=provider_summary,
    )

    print(
        provider_summary
        .to_string(index=False)
    )

    print(
        "Analysis validation: PASS"
    )

    print_section(
        "6. INVESTIGATE OUTLIERS"
    )

    general_outliers = (
        investigate_billed_cost_outliers(
            clean_data
        )
    )

    print(
        "--- Top Five Billed Cost Rows ---"
    )

    print(
        general_outliers[
            "top5_highest"
        ]
        .to_string(index=False)
    )

    print(
        "\nBilled Cost Skewness: "
        f"{general_outliers['skewness']}"
    )

    print(
        "Global IQR Outlier Count: "
        f"{general_outliers['iqr_outlier_count']}"
    )

    service_outliers = (
        investigate_billed_cost_outliers_by_service(
            clean_data
        )
    )

    print(
        "Service-Level Outlier Count: "
        f"{service_outliers['outlier_count']}"
    )

    print(
        "\n--- Service-Level Outlier Summary ---"
    )

    print(
        service_outliers[
            "summary"
        ]
        .head(15)
        .to_string(index=False)
    )

    print_section(
        "7. SAVE CLEANED DATA"
    )

    CLEANED_BILLING_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    clean_data.to_csv(
        CLEANED_BILLING_FILE,
        index=False,
    )

    print(
        "Cleaned CSV saved successfully."
    )

    print(
        f"Output file: {CLEANED_BILLING_FILE}"
    )

    print(
        f"Saved rows: {len(clean_data)}"
    )

    print_section(
        "DATA PIPELINE: PASS"
    )

    return clean_data


def main() -> None:
    run_data_pipeline()


if __name__ == "__main__":
    main()