"""تشغيل استعلامات SQLite وحفظ نتائجها في تقرير واحد."""

import sqlite3

import pandas as pd

from src.config import (
    DATABASE_FILE,
    QUERIES_DIR,
    QUERY_RESULTS_FILE,
)


def run_queries():

    QUERY_RESULTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(
        DATABASE_FILE
    ) as connection:

        with QUERY_RESULTS_FILE.open(
            "w",
            encoding="utf-8",
        ) as output:

            # قراءة ملفات SQL وفق ترتيب أسمائها.
            query_files = sorted(
                QUERIES_DIR.glob("*.sql")
            )

            for query_file in query_files:

                output.write(
                    f"\n{'=' * 70}\n"
                    f"queries/{query_file.name}\n"
                    f"{'=' * 70}\n"
                )

                raw_sql = query_file.read_text(
                    encoding="utf-8"
                )

                statements = [
                    statement.strip()
                    for statement
                    in raw_sql.split(";")
                    if statement.strip()
                ]

                for statement in statements:

                    clean_sql = "\n".join(
                        line
                        for line
                        in statement.splitlines()
                        if not line
                        .strip()
                        .startswith("--")
                    ).strip()

                    if not clean_sql:
                        continue

                    # تنفيذ الاستعلام على SQLite.
                    result = pd.read_sql_query(
                        clean_sql,
                        connection,
                    )

                    # استخدام أول سطر كعنوان مختصر للاستعلام.
                    first_line = (
                        clean_sql
                        .splitlines()[0][:70]
                    )

                    output.write(
                        f"\n--- {first_line} ---\n"
                    )

                    output.write(
                        result.to_string(
                            index=False
                        )
                    )

                    output.write("\n")

    print(
        "SQL query report saved successfully."
    )

    print(
        f"Report: {QUERY_RESULTS_FILE}"
    )

    return QUERY_RESULTS_FILE


if __name__ == "__main__":
    run_queries()