# يوزع الصفوف والتكاليف حسب مزود وفترة فوترة.
SELECT
    ProviderName,

    DATE(
        SAFE_CAST(
            BillingPeriodStart AS TIMESTAMP
        )
    ) AS billing_period_start,

    DATE(
        SAFE_CAST(
            BillingPeriodEnd AS TIMESTAMP
        )
    ) AS billing_period_end,

    COUNT(*) AS charge_line_count,

    SUM(BilledCost) AS billed_cost,

    SUM(EffectiveCost) AS effective_cost

FROM `data-ai-assistant-training.cloud_finops.billing_pipeline_day2`

GROUP BY
    ProviderName,
    billing_period_start,
    billing_period_end

ORDER BY
    billing_period_start,
    ProviderName;