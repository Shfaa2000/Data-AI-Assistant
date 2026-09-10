import pandas as pd


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


def get_credit_rows(
    data: pd.DataFrame,
) -> pd.DataFrame:
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

    return data.loc[
        data["ChargeCategory"] == "Credit",
        columns,
    ]


def get_microsoft_negative_rows(
    data: pd.DataFrame,
) -> pd.DataFrame:
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

    mask = (
        data["ProviderName"] == "Microsoft"
    ) & (
        data["BilledCost"] < 0
    )

    return data.loc[
        mask,
        columns,
    ]


def get_microsoft_negative_summary(
    data: pd.DataFrame,
) -> pd.DataFrame:
    negative_rows = (
        get_microsoft_negative_rows(data)
    )

    return (
        negative_rows
        .groupby(
            [
                "ServiceName",
                "ServiceCategory",
                "ChargeDescription",
                "ConsumedUnit",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            RowCount=(
                "BilledCost",
                "size",
            ),
            TotalBilledCost=(
                "BilledCost",
                "sum",
            ),
            TotalEffectiveCost=(
                "EffectiveCost",
                "sum",
            ),
            TotalConsumedQuantity=(
                "ConsumedQuantity",
                "sum",
            ),
        )
    )


def get_commitment_rows(
    data: pd.DataFrame,
) -> pd.DataFrame:
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

    return data.loc[
        data["CommitmentDiscountId"].notna(),
        columns,
    ]


def get_commitment_summary(
    data: pd.DataFrame,
) -> pd.DataFrame:
    commitment_rows = (
        get_commitment_rows(data)
    )

    return (
        commitment_rows
        .groupby(
            [
                "CommitmentDiscountId",
                "CommitmentDiscountType",
                "CommitmentDiscountStatus",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            RowCount=(
                "BilledCost",
                "size",
            ),
            TotalBilledCost=(
                "BilledCost",
                "sum",
            ),
            TotalEffectiveCost=(
                "EffectiveCost",
                "sum",
            ),
        )
    )


def get_red_hat_marketplace_rows(
    data: pd.DataFrame,
) -> pd.DataFrame:
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

    mask = (
        data["PublisherName"]
        .str.contains(
            "Red Hat",
            case=False,
            na=False,
        )
    )

    return data.loc[
        mask,
        columns,
    ]


def get_oracle_adjustment_rows(
    data: pd.DataFrame,
) -> pd.DataFrame:
    mask = (
        data["ProviderName"] == "Oracle"
    ) & (
        data["ChargeCategory"] == "Adjustment"
    )

    return data.loc[mask]


def get_story_view(
    rows: pd.DataFrame,
    n: int = 1,
) -> pd.DataFrame:
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

def flag_billed_cost_outliers_by_service(
    data: pd.DataFrame,
    min_group_size: int = 4,
) -> pd.Series:
    """تحديد Outliers داخل كل Provider وService باستخدام IQR."""

    required_columns = {
        "ProviderName",
        "ServiceName",
        "BilledCost",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing columns for service outliers: "
            f"{sorted(missing_columns)}"
        )

    billed_cost = pd.to_numeric(
        data["BilledCost"],
        errors="raise",
    )

    grouped_cost = billed_cost.groupby(
        [
            data["ProviderName"],
            data["ServiceName"],
        ],
        dropna=False,
    )

    q1 = grouped_cost.transform(
        lambda values: values.quantile(0.25)
    )

    q3 = grouped_cost.transform(
        lambda values: values.quantile(0.75)
    )

    group_size = grouped_cost.transform(
        "count"
    )

    iqr = q3 - q1

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    # هذا المتغير عبارة عن Boolean Series بنفس عدد صفوف البيانات. كل صف سيحصل على True أو False.
    eligible_group = (
        billed_cost.notna()
        & group_size.ge(min_group_size)
        # هل استطعنا حساب IQR لهذه المجموعة؟
        & iqr.notna()
    )

    return (
        eligible_group
        & (
            (billed_cost < lower_bound)
            | (billed_cost > upper_bound)
        )
    )

def investigate_billed_cost_outliers_by_service(
    data: pd.DataFrame,
    #فإن المجموعة التي تحتوي على أربعة سجلات أو أكثر مؤهلة للتحليل.
    min_group_size: int = 4,
) -> dict:
    """إنتاج ملخص Outliers لكل Provider وService."""

    outlier_flag = (
        flag_billed_cost_outliers_by_service(
            data,
            min_group_size=min_group_size,
        )
    )
    # assign يعيد DataFrame جديدة تحتوي على جميع الأعمدة الأصلية، إضافة إلى:
    marked_data = data.assign(
        BilledCost_outlier_by_service=outlier_flag
    )

    summary = (
        marked_data
        .groupby(
            [
                "ProviderName",
                "ServiceName",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(
            RowCount=(
                "BilledCost",
                "size",
            ),
            OutlierCount=(
                "BilledCost_outlier_by_service",
                "sum",
            ),
            MinBilledCost=(
                "BilledCost",
                "min",
            ),
            MaxBilledCost=(
                "BilledCost",
                "max",
            ),
        )
    )
    # # احسب نسبة Outliers من إجمالي صفوف كل مجموعة.
    summary["OutlierRatePct"] = (
        100
        * summary["OutlierCount"]
        / summary["RowCount"]
    ).round(2)

    summary = (
        summary
        .loc[summary["OutlierCount"] > 0]
        .sort_values(
            [
                "OutlierCount",
                "OutlierRatePct",
            ],
            ascending=False,
        )
    )

    detail_columns = [
        "ProviderName",
        "ServiceName",
        "ServiceCategory",
        "ChargeCategory",
        "ChargeDescription",
        "BilledCost",
        "EffectiveCost",
    ]

    available_columns = [
        column
        for column in detail_columns
        if column in data.columns
    ]

    outlier_rows = (
        data
        .loc[outlier_flag, available_columns]
        .sort_values(
            "BilledCost",
            ascending=False,
        )
    )

    return {
        "method": "IQR within ProviderName + ServiceName",
        "minimum_group_size": min_group_size,
        "outlier_count": int(outlier_flag.sum()),
        "summary": summary,
        "outlier_rows": outlier_rows,
    }


def investigate_billed_cost_outliers(
    data: pd.DataFrame,
) -> dict:
    top5 = data.nlargest(
        5,
        "BilledCost",
    )[
        [
            "ProviderName",
            "ServiceName",
            "BilledCost",
            "ChargeDescription",
        ]
    ]

    stats = (
        data["BilledCost"]
        .describe()
    )

    skewness = (
        data["BilledCost"]
        .skew()
    )

    q1, q3 = data[
        "BilledCost"
    ].quantile(
        [0.25, 0.75]
    )

    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    outliers = data[
        (data["BilledCost"] < lower)
        | (data["BilledCost"] > upper)
    ]

    return {
        "top5_highest": top5,
        "descriptive_stats": stats,
        "skewness": skewness,
        "iqr_outlier_count": len(outliers),
        "iqr_outliers_by_category": (
            outliers["ServiceCategory"]
            .value_counts()
        ),
    }