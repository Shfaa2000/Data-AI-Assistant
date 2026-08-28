-- Q15: تصنيف الصفوف حسب حجم التكلفة (CASE بسيط)
SELECT
    CASE
        WHEN BilledCost > 1 THEN 'High'
        WHEN BilledCost > 0 THEN 'Medium'
        ELSE 'Zero or Negative'
    END AS CostTier,
    COUNT(*) AS RowCount
FROM billing
GROUP BY CostTier;
-- توجيه: قارني هالتوزيع بالـskewness يلي حسبناها بالأسبوع الثاني — لازم "Zero or Negative"
-- يكون فيها أكبر عدد بفارق كبير، وهذا دليل رقمي إضافي على نفس الالتواء الشديد.

-- Q16: اختبار خطر التضاعف (Cardinality check قبل أي JOIN مستقبلي)
SELECT COUNT(*) AS RowsBeforeJoin FROM billing;
-- توجيه: احفظي هالرقم (1000) كمرجع. أي JOIN تسويه لاحقاً (لو ضفتي جدول Provider منفصل
