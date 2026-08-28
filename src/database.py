import sqlite3
import pandas as pd

clean_data = pd.read_csv("data/processed/billing_cleaned.csv")
connection = sqlite3.connect("database.sqlite")
clean_data.to_sql("billing", connection, if_exists="replace", index=False)
connection.close()

0
query1 = """
SELECT ProviderName, 
       COUNT(*) AS RowCount, 
       SUM(BilledCost) AS TotalBilledCost
FROM billing
GROUP BY ProviderName;
"""
result = pd.read_sql(query1, connection)
print(result)

query2 = """
SELECT ProviderName, ChargeCategory, SUM(BilledCost) AS Total
FROM billing
WHERE BilledCost < 0
GROUP BY ProviderName, ChargeCategory
HAVING SUM(BilledCost) < 0;
"""
print(pd.read_sql(query2, connection
                  ))

query3 = """
SELECT COUNT(*) AS TotalRows, 
       COUNT(ResourceName) AS NonNullResourceName,
       COUNT(AvailabilityZone) AS NonNullAZ
FROM billing;
"""
print(pd.read_sql(query3, connection))


