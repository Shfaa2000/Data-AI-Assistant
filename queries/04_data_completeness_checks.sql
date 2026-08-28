-- Q11: COUNT(*) مقابل COUNT(column) — يفضح الفقدان الحقيقي
SELECT COUNT(*) AS TotalRows,
       COUNT(ResourceName) AS NonNullResourceName,
       COUNT(AvailabilityZone) AS NonNullAZ
FROM billing;
-- المعلومة: الفرق بين TotalRows و NonNullResourceName = عدد القيم الفاضية فعلياً (949).

-- Q12: صفوف فيها ResourceName فاضي فعلياً (IS NULL الصحيحة، مش = NULL)
SELECT COUNT(*) AS MissingResourceName
FROM billing
WHERE ResourceName IS NULL;
-- توجيه (فكري): ليش WHERE ResourceName = NULL ما بيشتغل بـSQL، ولازم IS NULL بالتحديد؟
-- (تلميح: NULL مش "قيمة" تقدري تقارنيها بـ=، هي "غياب قيمة").

-- Q13: التحقق من تصنيف الأعمدة عالية الفقدان (Not Applicable مقابل Missing)
SELECT
    COUNT(*) AS TotalRows,
    COUNT(ChargeClass) AS ChargeClass_NotNull,
    COUNT(CommitmentDiscountName) AS CommitmentDiscountName_NotNull,
    COUNT(ResourceName) AS ResourceName_NotNull,
    COUNT(ResourceType) AS ResourceType_NotNull
FROM billing;
-- المعلومة: هاد استعلام إثبات رقمي لقرار decision_log رقم 4 — ChargeClass/CommitmentDiscountName
-- لازم يطلعوا 0 بالكامل (Not Applicable)، وResourceName/ResourceType فقدان جزئي (Missing متوقع).

-- Q14: أعلى وأدنى BilledCost لكل Provider
SELECT ProviderName, MIN(BilledCost) AS MinCost, MAX(BilledCost) AS MaxCost
FROM billing
GROUP BY ProviderName;
