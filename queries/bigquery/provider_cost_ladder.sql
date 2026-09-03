# هل طبقات التكلفة الأربع متوفرة وقابلة للمقارنة لكل Provider؟ وما مقدار الفجوات بينها؟
SELECT
    ProviderName,
    BillingCurrency,

    COUNT(*) AS charge_line_count,
    # التكلفة النظرية بسعر القائمة قبل خصومات العقد.
    COUNT(ListCost) AS list_cost_available_rows,
    # التكلفة حسب السعر المتفق عليه في العقد قبل تأثيرات أخرى مثل بعض الالتزامات.
    COUNT(ContractedCost) AS contracted_cost_available_rows,

    COUNT(BilledCost) AS billed_cost_available_rows,
    # التكلفة الاقتصادية المعترف بها للفترة بعد توزيع بعض الالتزامات أو الخصومات.
    COUNT(EffectiveCost) AS effective_cost_available_rows,

    COUNTIF(
        ListCost IS NOT NULL
        AND ContractedCost IS NOT NULL
    ) AS list_contracted_comparable_rows,

    COUNTIF(
        ContractedCost IS NOT NULL
        AND BilledCost IS NOT NULL
    ) AS contracted_billed_comparable_rows,

    COUNTIF(
        BilledCost IS NOT NULL
        AND EffectiveCost IS NOT NULL
    ) AS billed_effective_comparable_rows,

    SUM(ListCost) AS list_cost,

    SUM(ContractedCost) AS contracted_cost,

    SUM(BilledCost) AS billed_cost,

    SUM(EffectiveCost) AS effective_cost,

    SUM(
        ListCost - ContractedCost
    ) AS list_to_contracted_gap,

    SUM(
        ContractedCost - BilledCost
    ) AS contracted_to_billed_gap,

    SUM(
        BilledCost - EffectiveCost
    ) AS billed_to_effective_gap

FROM `data-ai-assistant-training.cloud_finops.billing_pipeline_day2`

GROUP BY
    ProviderName,
    BillingCurrency

ORDER BY
    ProviderName,
    BillingCurrency;