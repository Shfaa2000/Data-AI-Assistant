"""حفظ البيانات المنظفة داخل قاعدة SQLite محلية."""

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import (
    CLEANED_BILLING_FILE,
    DATABASE_FILE,
)


def save_cleaned_data_to_sqlite(
    source_file: Path = CLEANED_BILLING_FILE,
    database_file: Path = DATABASE_FILE,
) -> int:

    source_file = Path(source_file)
    database_file = Path(database_file)

    if not source_file.is_file():
        raise FileNotFoundError(
            "Cleaned billing file was not found: "
            f"{source_file}"
        )

    clean_data = pd.read_csv(
        source_file
    )

    if clean_data.empty:
        raise ValueError(
            "The cleaned billing file contains no rows."
        )

    database_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with sqlite3.connect(
        database_file
    ) as connection:
        clean_data.to_sql(
            "billing",
            connection,
            if_exists="replace",
            index=False,
        )

    print(
        "SQLite table saved successfully."
    )

    print(
        f"Database: {database_file}"
    )

    print(
        f"Rows saved: {len(clean_data)}"
    )

    return len(clean_data)


if __name__ == "__main__":
    save_cleaned_data_to_sqlite()