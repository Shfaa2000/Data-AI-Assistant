import pandas as pd


def get_provider_summary(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.groupby(
            "ProviderName",
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("ProviderName", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
            AverageBilledCost=("BilledCost", "mean"),
            MinBilledCost=("BilledCost", "min"),
            MaxBilledCost=("BilledCost", "max"),
        )
    )


def get_provider_charge_summary(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.groupby(
            ["ProviderName", "ChargeCategory"],
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
        )
    )


def get_provider_service_summary(data: pd.DataFrame) -> pd.DataFrame:
    return (
        data.groupby(
            ["ProviderName", "ServiceCategory"],
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
        )
    )


def get_negative_cost_summary(data: pd.DataFrame) -> pd.DataFrame:
    negative_rows = data.loc[data["BilledCost"] < 0]

    return (
        negative_rows.groupby(
            [
                "ProviderName",
                "ChargeCategory",
                "ServiceCategory",
            ],
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
        )
    )


def get_zero_cost_summary(data: pd.DataFrame) -> pd.DataFrame:
    zero_rows = data.loc[data["BilledCost"] == 0]

    return (
        zero_rows.groupby(
            [
                "ProviderName",
                "ChargeCategory",
                "ServiceCategory",
            ],
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("BilledCost", "size")
        )
    )


def get_top_services(data: pd.DataFrame,n: int = 10) -> pd.DataFrame:
    return (
        data.groupby(
            ["ProviderName", "ServiceName"],
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
        )
        .sort_values(
            "TotalBilledCost",
            ascending=False
        )
        .head(n)
    )


def get_top_subaccounts(data: pd.DataFrame,n: int = 10) -> pd.DataFrame:
    return (
        data.groupby(
            "SubAccountName",
            as_index=False,
            dropna=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
        )
        .sort_values(
            "TotalBilledCost",
            ascending=False
        )
        .head(n)
    )


def get_analysis_results(data: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "Provider Summary":
            get_provider_summary(data),

        "Provider + Charge Category":
            get_provider_charge_summary(data),

        "Provider + Service Category":
            get_provider_service_summary(data),

        "Negative Costs":
            get_negative_cost_summary(data),

        "Zero Costs":
            get_zero_cost_summary(data),

        "Top 10 Services":
            get_top_services(data),

        "Top 10 SubAccounts":
            get_top_subaccounts(data),
    }