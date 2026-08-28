import pandas as pd
import json
from collections import Counter

def normalize_charge_frequency(series: pd.Series) -> pd.Series:
    """توحيد صيغة ChargeFrequency (Usage-Based / Usage-based / One-Time) بصيغة واحدة."""
    return series.str.strip().str.title()


def flag_unreliable_availability_zone(data: pd.DataFrame) -> pd.Series:
    looks_numeric = data["AvailabilityZone"].astype(str).str.match(r'^-?\d')
    return ~looks_numeric.fillna(False)


def clean_billing_data(data: pd.DataFrame) -> pd.DataFrame:
    """   تاخد البيانات الخام وترجع نسخة نظيفة، بدون فقدان أي عمود أصلي."""
    clean = data.copy()
    clean["ChargeFrequency_normalized"] = normalize_charge_frequency(clean["ChargeFrequency"])
    clean["AvailabilityZone_valid"] = flag_unreliable_availability_zone(clean)
    clean["BilledCost_outlier_adjusted"] = flag_billed_cost_outliers_adjusted(clean)
    return clean


def extract_normalized_tag_keys(tag_json) -> list:
    """يرجع مفاتيح Tags بعد التطبيع (lowercase + strip) لصف واحد."""
    try:
        parsed = json.loads(tag_json)
    except (TypeError, json.JSONDecodeError):
        return []
    return [k.strip().lower() for k in parsed.keys()]


def get_tag_key_frequency(data: pd.DataFrame) -> Counter:
    """تكرار كل مفتاح Tag بعد التطبيع عبر كل الـdataset — للاستكشاف فقط، مو جزء من clean_billing_data."""
    all_keys = data["Tags"].dropna().apply(extract_normalized_tag_keys)
    return Counter(k for keys in all_keys for k in keys)

def flag_billed_cost_outliers(data: pd.DataFrame) -> pd.Series:
    """يعلّم الصفوف اللي BilledCost تبعها outlier بطريقة IQR — للمراجعة، مش للحذف."""
    Q1, Q3 = data["BilledCost"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    lower, upper = Q1 - 1.5*IQR, Q3 + 1.5*IQR
    return ~data["BilledCost"].between(lower, upper)


def flag_billed_cost_outliers_adjusted(data: pd.DataFrame) -> pd.Series:

    x = data["BilledCost"].values

    # 1) نلاقي نقطة المنتصف
    med = pd.Series(x).median()

    # 2) نقسم البيانات لمجموعتين حوالين المنتصف
    xi = x[x <= med]   # تحت أو يساوي المنتصف
    xj = x[x >= med]   # فوق أو يساوي المنتصف

    # 3) نحسب "قديش كل زوج بعيد بشكل غير متماثل عن المنتصف"
    h_vals = [((j - med) - (med - i)) / (j - i) for i in xi for j in xj if i != j]

    # 4) medcouple = الوسيط (median) لكل قيم h
    mc = pd.Series(h_vals).median()

    # 5) نحسب IQR العادية
    Q1, Q3 = data["BilledCost"].quantile([0.25, 0.75])
    IQR = Q3 - Q1

    # 6) نبني حدود غير متماثلة حسب اتجاه الالتواء (mc)
    if mc >= 0:  # التواء ناحية اليمين (حالتنا بالضبط)
        lower = Q1 - 1.5 * (2.718281828 ** (-4*mc)) * IQR
        upper = Q3 + 1.5 * (2.718281828 ** (3*mc)) * IQR
    else:        # التواء ناحية اليسار
        lower = Q1 - 1.5 * (2.718281828 ** (-3*mc)) * IQR
        upper = Q3 + 1.5 * (2.718281828 ** (4*mc)) * IQR

    return ~data["BilledCost"].between(lower, upper)