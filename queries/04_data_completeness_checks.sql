-- Q11: عدد الصفوف والقيم غير الفارغة
SELECT
    COUNT(*) AS TotalRows,
    COUNT(ResourceName) AS NonNullResourceName,
    COUNT(AvailabilityZone) AS NonNullAZ
FROM billing;


-- Q12: عدد ResourceName الفارغة
SELECT
    COUNT(*) AS MissingResourceName
FROM billing
WHERE ResourceName IS NULL;


-- Q13: فحص الأعمدة عالية الفقدان
SELECT
    COUNT(*) AS TotalRows,
    COUNT(ChargeClass)
        AS ChargeClass_NotNull,
    COUNT(CommitmentDiscountName)
        AS CommitmentDiscountName_NotNull,
    COUNT(ResourceName)
        AS ResourceName_NotNull,
    COUNT(ResourceType)
        AS ResourceType_NotNull
FROM billing;


-- Q14: أعلى وأدنى BilledCost لكل Provider
SELECT
    ProviderName,
    MIN(BilledCost) AS MinCost,
    MAX(BilledCost) AS MaxCost
FROM billing
GROUP BY ProviderName;