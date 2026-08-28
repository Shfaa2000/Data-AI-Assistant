-- Q4: نسبة الصفوف الصفرية والسالبة حسب ChargeCategory
SELECT ChargeCategory,
       SUM(CASE WHEN BilledCost = 0 THEN 1 ELSE 0 END) AS ZeroCount,
       SUM(CASE WHEN BilledCost < 0 THEN 1 ELSE 0 END) AS NegativeCount,
       COUNT(*) AS TotalCount
FROM billing
GROUP BY ChargeCategory;

-- Q5: القيم السالبة — Credit صريح مقابل تصحيح مدمج (يوثق اكتشاف AWS/Microsoft بلغة SQL)
SELECT ProviderName,
       CASE
           WHEN ChargeDescription LIKE '%Credit%' OR ChargeDescription LIKE '%Promotional%' THEN 'Explicit Credit'
           ELSE 'Embedded Adjustment'
       END AS NegativeType,
       COUNT(*) AS RowCount,
       SUM(BilledCost) AS TotalAmount
FROM billing
WHERE BilledCost < 0
GROUP BY ProviderName, NegativeType;

-- Q6: التحقق من صحة صف الـCredit (WHERE + HAVING)
SELECT ProviderName, ChargeCategory, SUM(BilledCost) AS Total
FROM billing
WHERE BilledCost < 0
GROUP BY ProviderName, ChargeCategory
HAVING SUM(BilledCost) < 0;
