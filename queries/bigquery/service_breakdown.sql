# استعلام تفصيلي قابل لإعادة الاستخدام لخدمة واحدة يختارها المستخدم.
SELECT
    ServiceCategory AS service_category,
    ChargeCategory AS charge_category,
    COUNT(*) AS charge_line_count,
    SUM(BilledCost) AS billed_cost,
    SUM(IF(BilledCost > 0, BilledCost, 0)) AS positive_billed_cost,
    SUM(IF(BilledCost < 0, BilledCost, 0)) AS negative_billed_cost,
    SUM(EffectiveCost) AS effective_cost,
    COUNTIF(BilledCost < 0) AS negative_line_count,
    COUNTIF(BilledCost = 0) AS zero_billed_line_count
FROM `{source_table}`
#اسم Provider كـScalar Query Parameter.
WHERE ProviderName = @provider
  AND ServiceName = @service
  AND BillingCurrency = @currency
GROUP BY ServiceCategory, ChargeCategory
ORDER BY positive_billed_cost DESC, service_category, charge_category;