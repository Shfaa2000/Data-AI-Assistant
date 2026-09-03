# ما الخدمات ذات التكلفة الموجبة الأعلى، وأي خدمة تستحق أن نبدأ بتحليلها تفصيليا؟
SELECT
    ProviderName,
    ServiceName,
    BillingCurrency,
    service_categories,
    charge_line_count,
    billed_cost,
    positive_billed_cost,
    negative_billed_cost,
    effective_cost,
    billed_effective_gap,
    negative_line_count,
    zero_billed_line_count
FROM `data-ai-assistant-training.cloud_finops.v_service_costs`
ORDER BY
    positive_billed_cost DESC,
    ProviderName,
    ServiceName;