# Reconciliation — pandas (main.py) vs SQL

## 1. Provider Summary
| Provider | pandas RowCount | SQL RowCount | pandas TotalBilled | SQL TotalBilled | الحالة |
|---|---|---|---|---|---|
| AWS | 942 | 942 | 18.006639 | 18.006639 | ✅ مطابق تماماً |
| Microsoft | 51 | 51 | 1.976514 | 1.976514 | ✅ مطابق تماماً |
| Oracle | 7 | 7 | 0.537074 | 0.537074 | ✅ مطابق تماماً |

## 2. Top Service (EC2)
| المصدر | TotalBilledCost |
|---|---|
| pandas (main.py) | 16.041693 |
| SQL (Q7) | 16.041693 |
| الحالة | ✅ مطابق تماماً |

## 3. Negative Rows Count
| المصدر | العدد |
|---|---|
| main.py (الأسبوع الثاني) | 13 |
| SQL (Q4: Credit=1 + Usage negative=12) | 13 |
| الحالة | ✅ مطابق تماماً |

## 4. Zero-Cost Rows
| المصدر | العدد |
|---|---|
| main.py (الأسبوع الأول) | 329 |
| SQL (Q4: ZeroCount تحت Usage) | 329 |
| الحالة | ✅ مطابق تماماً |

## خلاصة
5 نتائج رئيسية اختُبرت، **صفر اختلافات**. الـpipeline (ingestion → cleaning → analytics)
مثبت رياضياً أنه متسق مع طبقة SQL المستقلة بالكامل.