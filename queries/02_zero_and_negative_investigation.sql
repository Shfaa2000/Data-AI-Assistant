-- Q4: الصفوف الصفرية والسالبة حسب ChargeCategory
SELECT
    ChargeCategory,
    SUM(
        CASE
            WHEN BilledCost = 0 THEN 1
            ELSE 0
        END
    ) AS ZeroCount,
    SUM(
        CASE
            WHEN BilledCost < 0 THEN 1
            ELSE 0
        END
    ) AS NegativeCount,
    COUNT(*) AS TotalCount
FROM billing
GROUP BY ChargeCategory;


-- Q5: تصنيف القيم السالبة دون افتراض سبب غير مثبت
SELECT
    ProviderName,
    CASE
        WHEN ChargeCategory = 'Credit'
            THEN 'Explicit Credit'
        ELSE 'Unclassified Negative Charge'
    END AS NegativeType,
    COUNT(*) AS RowCount,
    SUM(BilledCost) AS TotalAmount
FROM billing
WHERE BilledCost < 0
GROUP BY
    ProviderName,
    NegativeType;


-- Q6: القيم السالبة حسب Provider وChargeCategory
SELECT
    ProviderName,
    ChargeCategory,
    SUM(BilledCost) AS Total
FROM billing
WHERE BilledCost < 0
GROUP BY
    ProviderName,
    ChargeCategory
HAVING SUM(BilledCost) < 0;