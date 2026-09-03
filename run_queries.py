import sqlite3

import pandas as pd

from src.config import (
    DATABASE_FILE,
    QUERIES_DIR,
    REPORTS_DIR,
)


query_results_file = (
    REPORTS_DIR / "query_results.txt"
)

with sqlite3.connect(
    DATABASE_FILE
) as connection:

    with open(
        query_results_file,
        "w",
        encoding="utf-8",
    ) as output:

        for filepath in sorted(
            QUERIES_DIR.glob("*.sql")
        ):
            output.write(
                f"\n{'=' * 70}\n"
                f" queries/{filepath.name}\n"
                f"{'=' * 70}\n"
            )

            with open(
                filepath,
                encoding="utf-8",
            ) as query_file:
                raw_queries = query_file.read()

            statements = [
                statement.strip()
                for statement in raw_queries.split(";")
                if statement.strip()
            ]

            for statement in statements:
                clean_lines = [
                    line
                    for line in statement.splitlines()
                    if not line.strip().startswith("--")
                ]

                clean_statement = (
                    "\n".join(clean_lines).strip()
                )

                if not clean_statement:
                    continue

                output.write(
                    "\n--- "
                    f"{clean_statement.splitlines()[0][:70]}"
                    " ---\n"
                )

                try:
                    result = pd.read_sql(
                        clean_statement,
                        connection,
                    )

                    output.write(
                        str(result) + "\n"
                    )

                except Exception as error:
                    output.write(
                        f"Error: {error}\n"
                    )

print(
    f"تم حفظ النتائج في: "
    f"{query_results_file}"
)