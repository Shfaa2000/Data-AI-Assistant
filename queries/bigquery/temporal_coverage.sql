#  يفحص التغطية الزمنية وجودة بدايات التواريخ.
SELECT
    ProviderName,
    BillingCurrency,

    MIN(
        # يحاول تحويل القيمة إلى النوع المطلوب. إذا فشل التحويل يعيد NULL بدلا من إسقاط الاستعلام.
        SAFE_CAST(BillingPeriodStart AS TIMESTAMP)
    ) AS earliest_billing_period_start,

    MAX(
        SAFE_CAST(BillingPeriodEnd AS TIMESTAMP)
    ) AS latest_billing_period_end,

    MIN(
        SAFE_CAST(ChargePeriodStart AS TIMESTAMP)
    ) AS earliest_charge_period_start,

    MAX(
        SAFE_CAST(ChargePeriodEnd AS TIMESTAMP)
    ) AS latest_charge_period_end,

    COUNT(
        DISTINCT BillingPeriodStart
    ) AS distinct_billing_period_starts,

    COUNT(
        DISTINCT ChargePeriodStart
    ) AS distinct_charge_period_starts,

    COUNT(*) AS charge_line_count,

    COUNTIF(
        SAFE_CAST(BillingPeriodStart AS TIMESTAMP) IS NULL
    ) AS invalid_billing_period_start_count,

    COUNTIF(
        SAFE_CAST(ChargePeriodStart AS TIMESTAMP) IS NULL
    ) AS invalid_charge_period_start_count,

    SUM(BilledCost) AS billed_cost,

    SUM(EffectiveCost) AS effective_cost

FROM `data-ai-assistant-training.cloud_finops.billing_pipeline_day2`

GROUP BY
    ProviderName,
    BillingCurrency

ORDER BY
    ProviderName,
    BillingCurrency;



