from src.analytics import get_analysis_results
from src.config import BILLING_FILE
from src.ingestion import load_data
from src.profiling import profile_data
from src.validation import (validate_analysis,validate_required_columns)


def print_result(title, result):
    print(f"\n=== {title} ===")
    print(result)


def main():
    data = load_data(BILLING_FILE)

    validate_required_columns(data)

    analysis_results = get_analysis_results(data)

    provider_summary = (analysis_results["Provider Summary"])

    validate_analysis(data,provider_summary)

    print("\nAll validation checks passed.")

    #for title, result in (analysis_results.items()):
        #print_result(title,result)

    # profile_data(data)


if __name__ == "__main__":
    main()