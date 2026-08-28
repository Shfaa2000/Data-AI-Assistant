import pandas as pd
from src.cleaning import (flag_unreliable_availability_zone,normalize_charge_frequency,
                          clean_billing_data, extract_normalized_tag_keys,get_tag_key_frequency)


def test_normalize_charge_frequency_unifies_case():
    series = pd.Series(["Usage-Based", "usage-based", "USAGE-BASED"])
    result = normalize_charge_frequency(series)
    assert result.nunique() == 1

def test_flag_availability_zone_detects_numeric():
    data = pd.DataFrame({"AvailabilityZone": ["us-east-1a", "0.045", None]})
    result = flag_unreliable_availability_zone(data)
    assert result.tolist() == [True, False, True]  # None يُعتبر موثوق (فاضي مش غلط)

def test_clean_billing_data_preserves_row_count():
    sample = pd.DataFrame({
        "ChargeFrequency": ["Usage-Based"],
        "AvailabilityZone": ["us-east-1a"],
         "BilledCost": [10.0]
    })
    result = clean_billing_data(sample)
    assert len(result) == len(sample)


def test_extract_normalized_tag_keys_lowercases_and_strips():
    # مثال فيه مسافات وحرف كبير — بتتأكد إنه التنظيف صار صح
    result = extract_normalized_tag_keys('{" Environment ": "prod"}')
    assert result == ["environment"]

def test_extract_normalized_tag_keys_handles_invalid_json():
    # مثال نص مش JSON إطلاقاً — بتتأكد إنه ما ينهار البرنامج
    assert extract_normalized_tag_keys("not json") == []

def test_extract_normalized_tag_keys_handles_none():
    # مثال قيمة فاضية — نفس فكرة try/except يلي شرحناها فوق
    assert extract_normalized_tag_keys(None) == []

def test_get_tag_key_frequency_counts_correctly():
    # جدول مصغّر فيه env وEnv (بحالة مختلفة) — بتتأكد إنه انعدّوا كمفتاح واحد
    data = pd.DataFrame({"Tags": ['{"env": "prod"}', '{"Env": "dev"}']})
    result = get_tag_key_frequency(data)
    assert result["env"] == 2

# python -m pytest tests/test_cleaning.py -v