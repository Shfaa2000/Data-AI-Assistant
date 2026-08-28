from src.analytics import get_analysis_results
from src.config import BILLING_FILE
from src.ingestion import load_data
from src.profiling import profile_data
from src.validation import (validate_analysis, validate_required_columns)
from src.cleaning import clean_billing_data
from src.investigations import investigate_billed_cost_outliers


def print_result(title, result):
    print(f"\n=== {title} ===")
    print(result)


def main():
    data = load_data(BILLING_FILE)
    validate_required_columns(data)

    # التنظيف + الحفظ
    clean_data = clean_billing_data(data)
    assert clean_data.shape[0] == data.shape[0], "لازم نفس عدد الصفوف بعد التنظيف"
    clean_data.to_csv("data/processed/billing_cleaned.csv", index=False)

    # التحقيق بالـoutliers 
    outlier_report = investigate_billed_cost_outliers(data)
    print(outlier_report["top5_highest"])
    print(f"Skewness: {outlier_report['skewness']}")
    print(f"عدد outliers حسب IQR: {outlier_report['iqr_outlier_count']}")

    # التحليل الأساسي
    analysis_results = get_analysis_results(data)
    provider_summary = analysis_results["Provider Summary"]
    validate_analysis(data, provider_summary)
    print("\nAll validation checks passed.")


if __name__ == "__main__":
    main()