import sqlite3
import pandas as pd
import glob

conn = sqlite3.connect("data/database.sqlite")

with open("query_results.txt", "w") as out:
    for filepath in sorted(glob.glob("queries/*.sql")):
        out.write(f"\n{'='*70}\n {filepath}\n{'='*70}\n")
        with open(filepath, encoding="utf-8") as f:
            raw = f.read()
        statements = [s.strip() for s in raw.split(";") if s.strip()]
        for stmt in statements:
            clean_lines = [l for l in stmt.split("\n") if not l.strip().startswith("--")]
            clean_stmt = "\n".join(clean_lines).strip()
            if not clean_stmt:
                continue
            out.write(f"\n--- {clean_stmt.splitlines()[0][:70]} ---\n")
            try:
                out.write(str(pd.read_sql(clean_stmt, conn)) + "\n")
            except Exception as e:
                out.write(f" Error: {e}\n")

print(" تم الحفظ في query_results.txt")