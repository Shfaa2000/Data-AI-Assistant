-- Q7: أعلى خمس خدمات حسب TotalBilledCost
SELECT
    ServiceName,
    SUM(BilledCost) AS TotalBilled
FROM billing
GROUP BY ServiceName
ORDER BY TotalBilled DESC
LIMIT 5;


-- Q8: ترتيب الخدمات داخل كل Provider
SELECT
    ProviderName,
    ServiceName,
    SUM(BilledCost) AS Total,
    RANK() OVER (
        PARTITION BY ProviderName
        ORDER BY SUM(BilledCost) DESC
    ) AS Rank
FROM billing
GROUP BY
    ProviderName,
    ServiceName;


-- Q9: عدد ResourceId المختلفة لكل Provider
SELECT
    ProviderName,
    COUNT(
        DISTINCT ResourceId
    ) AS DistinctResources
FROM billing
WHERE ResourceId IS NOT NULL
GROUP BY ProviderName;


-- Q10: عدد الصفوف حسب ServiceCategory
SELECT
    ServiceCategory,
    COUNT(*) AS RowCount
FROM billing
GROUP BY ServiceCategory
ORDER BY RowCount DESC;