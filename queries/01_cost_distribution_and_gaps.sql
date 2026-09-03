-- Q1: توزيع BilledCost وEffectiveCost حسب Provider
SELECT
    ProviderName,
    COUNT(*) AS RowCount,
    SUM(BilledCost) AS TotalBilled,
    SUM(EffectiveCost) AS TotalEffective,
    ROUND(
        SUM(BilledCost) - SUM(EffectiveCost),
        4
    ) AS Gap
FROM billing
GROUP BY ProviderName;


-- Q2: متوسط BilledCost لكل Provider
SELECT
    ProviderName,
    ROUND(
        AVG(BilledCost),
        6
    ) AS AvgBilledCost
FROM billing
GROUP BY ProviderName;


-- Q3: أعلى الخدمات حسب فرق BilledCost وEffectiveCost
WITH gap_by_service AS (
    SELECT
        ServiceName,
        SUM(BilledCost) AS TotalBilled,
        SUM(EffectiveCost) AS TotalEffective,
        SUM(BilledCost)
            - SUM(EffectiveCost) AS Gap
    FROM billing
    GROUP BY ServiceName
)
SELECT *
FROM gap_by_service
ORDER BY ABS(Gap) DESC
LIMIT 5;