-- Q15: تصنيف استكشافي للصفوف حسب BilledCost
SELECT
    CASE
        WHEN BilledCost > 1
            THEN 'High'
        WHEN BilledCost > 0
            THEN 'Medium'
        ELSE 'Zero or Negative'
    END AS CostTier,
    COUNT(*) AS RowCount
FROM billing
GROUP BY CostTier;


-- Q16: عدد الصفوف قبل تنفيذ أي JOIN
SELECT
    COUNT(*) AS RowsBeforeJoin
FROM billing;