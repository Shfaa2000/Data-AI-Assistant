# ينشئ طبقة تحليل مجمعة: صف واحد لكل خدمة ومزود وعملة.
WITH service_totals AS (
    SELECT
        BillingCurrency,
        ProviderName,
        ServiceName,
        STRING_AGG(
            DISTINCT ServiceCategory, ', ' ORDER BY ServiceCategory
        ) AS service_categories,
        COUNT(*) AS charge_line_count,
        SUM(BilledCost) AS billed_cost,
        SUM(IF(BilledCost > 0, BilledCost, 0)) AS positive_billed_cost,
        SUM(IF(BilledCost < 0, BilledCost, 0)) AS negative_billed_cost,
        SUM(EffectiveCost) AS effective_cost,
        COUNTIF(BilledCost < 0) AS negative_line_count,
        COUNTIF(BilledCost = 0) AS zero_billed_line_count
    FROM `{source_table}`
    GROUP BY BillingCurrency, ProviderName, ServiceName
)
SELECT
    *,
    billed_cost - effective_cost AS billed_effective_gap,
    100 * SAFE_DIVIDE(
        positive_billed_cost,
        SUM(positive_billed_cost) OVER (PARTITION BY BillingCurrency)
    ) AS positive_share_of_currency_pct,
    100 * SAFE_DIVIDE(
        positive_billed_cost,
        SUM(positive_billed_cost) OVER (
            PARTITION BY BillingCurrency, ProviderName
        )
    ) AS positive_share_of_provider_pct
FROM service_totals