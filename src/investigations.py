import pandas as pd

# تحقيقات خاصة بمشكلة أو anomaly
STORY_COLUMNS = [
    "ProviderName",
    "ServiceName",
    "ServiceCategory",
    "ResourceName",
    "ResourceType",
    "ChargeCategory",
    "ChargeDescription",
    "ConsumedQuantity",
    "ConsumedUnit",
    "BilledCost",
    "EffectiveCost",
    "RegionName",
]


def get_credit_rows(data: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "ProviderName",
        "ServiceName",
        "ServiceCategory",
        "ChargeCategory",
        "ChargeDescription",
        "ChargeFrequency",
        "BilledCost",
        "EffectiveCost",
        "ContractedCost",
        "ListCost",
        "PricingQuantity",
        "PricingUnit",
        "RegionName",
        "ResourceName",
        "SubAccountName",
    ]

    return data.loc[data["ChargeCategory"] == "Credit",columns]


def get_microsoft_negative_rows(data: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "ProviderName",
        "ServiceName",
        "ServiceCategory",
        "ResourceName",
        "ResourceType",
        "ChargeCategory",
        "ChargeDescription",
        "ChargeClass",
        "ChargeFrequency",
        "ConsumedQuantity",
        "ConsumedUnit",
        "PricingQuantity",
        "PricingUnit",
        "BilledCost",
        "EffectiveCost",
        "CommitmentDiscountId",
        "CommitmentDiscountType",
        "RegionName",
    ]

    return data.loc[(data["ProviderName"] == "Microsoft")& (data["BilledCost"] < 0),columns]


def get_microsoft_negative_summary(data: pd.DataFrame) -> pd.DataFrame:
    negative_rows = get_microsoft_negative_rows(data)

    return (
        negative_rows.groupby(
            [
                "ServiceName",
                "ServiceCategory",
                "ChargeDescription",
                "ConsumedUnit",
            ],
            dropna=False,
            as_index=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
            TotalConsumedQuantity=("ConsumedQuantity","sum"),
        )
    )


def get_commitment_rows(data: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "ProviderName",
        "ServiceName",
        "ServiceCategory",
        "ChargeCategory",
        "ChargeDescription",
        "CommitmentDiscountCategory",
        "CommitmentDiscountId",
        "CommitmentDiscountName",
        "CommitmentDiscountStatus",
        "CommitmentDiscountType",
        "PricingCategory",
        "PricingQuantity",
        "PricingUnit",
        "BilledCost",
        "EffectiveCost",
        "ContractedCost",
        "ListCost",
    ]

    return data.loc[data["CommitmentDiscountId"].notna(),
        columns
    ]


def get_commitment_summary(data: pd.DataFrame) -> pd.DataFrame:
    commitment_rows = get_commitment_rows(data)

    return (
        commitment_rows.groupby(
            [
                "CommitmentDiscountId",
                "CommitmentDiscountType",
                "CommitmentDiscountStatus",
            ],
            dropna=False,
            as_index=False
        )
        .agg(
            RowCount=("BilledCost", "size"),
            TotalBilledCost=("BilledCost", "sum"),
            TotalEffectiveCost=("EffectiveCost", "sum"),
        )
    )


def get_red_hat_marketplace_rows(data: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "ProviderName",
        "PublisherName",
        "InvoiceIssuerName",
        "ServiceName",
        "ServiceCategory",
        "ChargeCategory",
        "ChargeDescription",
        "BilledCost",
        "EffectiveCost",
    ]

    return data.loc[
        data["PublisherName"].str.contains(
            "Red Hat",
            case=False,
            na=False
        ),
        columns
    ]


def get_oracle_adjustment_rows(data: pd.DataFrame) -> pd.DataFrame:
    return data.loc[
        (data["ProviderName"] == "Oracle")
        & (data["ChargeCategory"]== "Adjustment")
    ]

def get_story_view(rows: pd.DataFrame,n: int = 1) -> pd.DataFrame:
    available_columns = [
        column
        for column in STORY_COLUMNS
        if column in rows.columns
    ]

    return (
        rows[available_columns]
        .head(n)
        .T
    )

def investigate_billed_cost_outliers(data: pd.DataFrame) -> dict:

    top5 = data.nlargest(5, "BilledCost")[
        ["ProviderName", "ServiceName", "BilledCost", "ChargeDescription"]
    ]
    stats = data["BilledCost"].describe()
    skewness = data["BilledCost"].skew()

    Q1, Q3 = data["BilledCost"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
    outliers = data[(data["BilledCost"] < lower) | (data["BilledCost"] > upper)]

    return {
        "top5_highest": top5,
        "descriptive_stats": stats,
        "skewness": skewness,
        "iqr_outlier_count": len(outliers),
        "iqr_outliers_by_category": outliers["ServiceCategory"].value_counts(),
    }