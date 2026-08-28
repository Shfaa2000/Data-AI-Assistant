-- Q7: أعلى 5 خدمات حسب TotalBilledCost
SELECT ServiceName, SUM(BilledCost) AS TotalBilled
FROM billing
GROUP BY ServiceName
ORDER BY TotalBilled DESC
LIMIT 5;

-- Q8: ترتيب الخدمات داخل كل Provider (Window Function)
SELECT ProviderName, ServiceName, SUM(BilledCost) AS Total,
       RANK() OVER (PARTITION BY ProviderName ORDER BY SUM(BilledCost) DESC) AS Rank
FROM billing
GROUP BY ProviderName, ServiceName;

-- Q9: كم Resource منفصل فعلياً شغال لكل Provider
SELECT ProviderName, COUNT(DISTINCT ResourceId) AS DistinctResources
FROM billing
WHERE ResourceId IS NOT NULL
GROUP BY ProviderName;
-- المعلومة : AWS=799, Microsoft=36, Oracle=7 موارد منفصلة فعلياً.
-- قارنيها بعدد الصفوف الكلي لكل provider (942/51/7) — AWS عندها 799 مورد بس 942 صف،
-- يعني بعض الموارد ظهرت أكتر من مرة (فترات فوترة مختلفة، بالضبط زي Rule 10 اللي وثقناها).
-- Microsoft فيها 36 مورد بس 51 صف — نفس النمط لكن أوضح نسبياً.

-- Q10: عدد الصفوف لكل ServiceCategory 
SELECT ServiceCategory, COUNT(*) AS RowCount
FROM billing
GROUP BY ServiceCategory
ORDER BY RowCount DESC;
