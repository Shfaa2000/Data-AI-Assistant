from src.analytics import get_analysis_results
from src.cleaning import clean_billing_data
from src.config import (
    BILLING_FILE,
    CLEANED_BILLING_FILE,
)
from src.ingestion import load_data
from src.investigations import (
    investigate_billed_cost_outliers,
)
from src.validation import (
    validate_analysis,
    validate_required_columns,
)


def main():
    data = load_data(BILLING_FILE)

    validate_required_columns(data)

    clean_data = clean_billing_data(data)

    assert clean_data.shape[0] == data.shape[0], (
        "لازم يبقى عدد الصفوف نفسه بعد التنظيف"
    )

    clean_data.to_csv(
        CLEANED_BILLING_FILE,
        index=False,
    )

    outlier_report = (
        investigate_billed_cost_outliers(
            data
        )
    )

    print(
        outlier_report["top5_highest"]
    )

    print(
        f"Skewness: "
        f"{outlier_report['skewness']}"
    )

    print(
        "عدد outliers حسب IQR: "
        f"{outlier_report['iqr_outlier_count']}"
    )

    analysis_results = (
        get_analysis_results(data)
    )

    provider_summary = (
        analysis_results["Provider Summary"]
    )

    validate_analysis(
        data,
        provider_summary,
    )

    print(
        "\nAll validation checks passed."
    )


if __name__ == "__main__":
    main()