"""طباعة وصف عام عن بيانات Cloud Billing."""

import pandas as pd


def profile_data(
    data: pd.DataFrame,
) -> None:

    print("\n--- First Five Rows ---")
    print(
        data.head()
        .to_string(index=False)
    )

    print("\n--- Dataset Shape ---")
    print(
        f"Rows: {len(data)}"
    )
    print(
        f"Columns: {len(data.columns)}"
    )

    print("\n--- Column Names ---")
    print(data.columns.tolist())

    print("\n--- Data Types ---")
    print(data.dtypes.to_string())

    print("\n--- DataFrame Info ---")
    data.info()

    missing_values = (
        data.isna()
        .sum()
        .sort_values(
            ascending=False
        )
    )

    print("\n--- Missing Values ---")
    print(missing_values.to_string())

    duplicate_count = int(
        data.duplicated().sum()
    )

    print("\n--- Duplicate Rows ---")
    print(duplicate_count)

    provider_counts = (
        data.groupby(
            "ProviderName",
            dropna=False,
        )
        .size()
        .reset_index(
            name="RowCount"
        )
        .sort_values(
            "RowCount",
            ascending=False,
        )
    )

    print("\n--- Provider Row Counts ---")
    print(
        provider_counts
        .to_string(index=False)
    )

    print("\n--- Financial Overview ---")

    print(
        "Total Billed Cost: "
        f"{data['BilledCost'].sum()}"
    )

    print(
        "Total Effective Cost: "
        f"{data['EffectiveCost'].sum()}"
    )

    negative_count = int(
        (data["BilledCost"] < 0).sum()
    )

    zero_count = int(
        (data["BilledCost"] == 0).sum()
    )

    positive_count = int(
        (data["BilledCost"] > 0).sum()
    )

    print(
        f"Negative Billed Cost Rows: {negative_count}"
    )

    print(
        f"Zero Billed Cost Rows: {zero_count}"
    )

    print(
        f"Positive Billed Cost Rows: {positive_count}"
    )