مبدأ Pareto/80-20: عدد قليل من الموارد (خصوصاً EC2) بيحرك معظم الفاتورة، بينما آلاف السجلات الصغيرة تأثيرها مهمل (skewness=3.17).
EC2 مموّهة تحت Storage: جزء كبير من "outliers" المصنفين Storage هم فعلياً تكلفة EBS مرتبطة بـEC2، مش تخزين مستقل — التركّز على EC2 أكبر مما يبدو ظاهرياً.
انزياح أعمدة عند Microsoft: AvailabilityZone كلها (51/51 صف) فيها قيم مأخوذة غلط من ContractedUnitPrice — دليل على مشكلة بمصدر البيانات (data pipeline) عند مزود واحد بالذات، مش عشوائية.



### Insight — EC2 مموّهة جزئياً تحت ServiceCategory=Storage
92% من outliers فئة Storage (23/25) هم فعلياً EBS volumes/Snapshots تابعين لـEC2،
مش خدمات تخزين مستقلة. يعني التركّز الفعلي على تكلفة EC2 أكبر مما يظهر عند تجميع
البيانات حسب ServiceCategory فقط — لازم نجمع Compute+Storage-tied-to-EC2 مع بعض
لفهم التكلفة الحقيقية لخدمة EC2 كاملة.

