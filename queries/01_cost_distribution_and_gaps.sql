-- Q1: كيف تتوزع Billed وEffective حسب كل Provider؟
-- الفايدة: نتحقق من مطابقة SQL مع نتيجة main.py (Provider Summary)، ونحسب Gap لكل provider
SELECT ProviderName,
       COUNT(*) AS RowCount,
       SUM(BilledCost) AS TotalBilled,
       SUM(EffectiveCost) AS TotalEffective,
       ROUND(SUM(BilledCost) - SUM(EffectiveCost), 4) AS Gap
FROM billing
GROUP BY ProviderName;
-- المعلومة (جاهزة): AWS أكبر Gap (5.006639)، مرتبط بوجود Savings Plans .
-- Oracle Gap = كامل TotalBilled لأنه EffectiveCost = صفر بكل صفوفها (قيد بيانات، مو نتيجة تحليل).

-- Q2: متوسط BilledCost لكل Provider — مقارنة بـAverageBilledCost 
SELECT ProviderName, ROUND(AVG(BilledCost), 6) AS AvgBilledCost
FROM billing
GROUP BY ProviderName;

-- Q3: أعلى Service حسب فرق Billed/Effective (CTE)
WITH gap_by_service AS (
    SELECT ServiceName,
           SUM(BilledCost) AS TotalBilled,
           SUM(EffectiveCost) AS TotalEffective,
           SUM(BilledCost) - SUM(EffectiveCost) AS Gap
    FROM billing
    GROUP BY ServiceName
)
SELECT * FROM gap_by_service
ORDER BY ABS(Gap) DESC
LIMIT 5;
