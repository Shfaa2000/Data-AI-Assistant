import json
from collections import Counter
import pandas as pd


def normalize_charge_frequency(
    series: pd.Series,
) -> pd.Series:
    """توحيد صيغة ChargeFrequency."""
    return series.str.strip().str.title()


def flag_unreliable_availability_zone(
    data: pd.DataFrame,
) -> pd.Series:
    """تحديد قيم AvailabilityZone الرقمية."""
    looks_numeric = (
        data["AvailabilityZone"]
        .astype(str)
        .str.match(r"^-?\d")
    )

    return ~looks_numeric.fillna(False)


def extract_normalized_tag_keys(
    tag_json,
) -> list:
    """استخراج مفاتيح Tags بعد التطبيع."""
    try:
        parsed = json.loads(tag_json)

    except (
        TypeError,
        json.JSONDecodeError,
    ):
        return []

    return [
        key.strip().lower()
        for key in parsed.keys()
    ]


def get_tag_key_frequency(
    data: pd.DataFrame,
) -> Counter:
    """حساب تكرار مفاتيح Tags."""
    all_keys = (
        data["Tags"]
        .dropna()
        .apply(extract_normalized_tag_keys)
    )

    return Counter(
        key
        for keys in all_keys
        for key in keys
    )


def flag_billed_cost_outliers(
    data: pd.DataFrame,
) -> pd.Series:
    """تحديد BilledCost outliers باستخدام IQR."""
    q1, q3 = data["BilledCost"].quantile(
        [0.25, 0.75]
    )

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    return ~data["BilledCost"].between(
        lower,
        upper,
    )


def flag_billed_cost_outliers_adjusted(
    data: pd.DataFrame,
) -> pd.Series:
    """تحديد BilledCost outliers باستخدام Adjusted Boxplot."""
    values = data["BilledCost"].values
    median = pd.Series(values).median()

    lower_values = values[
        values <= median
    ]

    upper_values = values[
        values >= median
    ]

    h_values = [
        ((upper - median) - (median - lower))
        / (upper - lower)
        for lower in lower_values
        for upper in upper_values
        if lower != upper
    ]

    medcouple = pd.Series(
        h_values
    ).median()

    q1, q3 = data["BilledCost"].quantile(
        [0.25, 0.75]
    )

    iqr = q3 - q1

    if medcouple >= 0:
        lower = (
            q1
            - 1.5
            * (2.718281828 ** (-4 * medcouple))
            * iqr
        )

        upper = (
            q3
            + 1.5
            * (2.718281828 ** (3 * medcouple))
            * iqr
        )

    else:
        lower = (
            q1
            - 1.5
            * (2.718281828 ** (-3 * medcouple))
            * iqr
        )

        upper = (
            q3
            + 1.5
            * (2.718281828 ** (4 * medcouple))
            * iqr
        )

    return ~data["BilledCost"].between(
        lower,
        upper,
    )


def clean_billing_data(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """إرجاع نسخة منظّمة دون حذف الصفوف."""
    clean = data.copy()

    clean["ChargeFrequency_normalized"] = (
        normalize_charge_frequency(
            clean["ChargeFrequency"]
        )
    )

    clean["AvailabilityZone_valid"] = (
        flag_unreliable_availability_zone(
            clean
        )
    )

    clean["BilledCost_outlier_adjusted"] = (
        flag_billed_cost_outliers_adjusted(
            clean
        )
    )

    return clean