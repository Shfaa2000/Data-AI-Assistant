import pandas as pd


def profile_data(data: pd.DataFrame) -> None:
    print("First five rows:")
    print(data.head())

    print("\nShape:", data.shape)

    print("\nColumns:")
    print(data.columns.tolist())

    print("\nData types:")
    print(data.dtypes)

    print("\nData info:")
    data.info()

    missing_counts = (
        data.isna().sum().sort_values(ascending=False))
    print("\nMissing values:")
    print(missing_counts)

    duplicate_count = data.duplicated().sum()
    print("\nDuplicate rows:", duplicate_count)

    provider_counts = (
        data.groupby("ProviderName", dropna=False)
        .size()
        .reset_index(name="RowCount")
        .sort_values("RowCount", ascending=False)
    )

    print("\nProvider counts:")
    print(provider_counts)

    print("\nTotal BilledCost:",data["BilledCost"].sum())

    print("\nTotal EffectiveCost:",data["EffectiveCost"].sum())

    negative_count = (data["BilledCost"] < 0).sum()
    zero_count = (data["BilledCost"] == 0).sum()
    positive_count = (data["BilledCost"] > 0).sum()

    print("\nNegative BilledCost values:",negative_count)
    print("Zero BilledCost values:",zero_count)
    print("Positive BilledCost values:",positive_count)