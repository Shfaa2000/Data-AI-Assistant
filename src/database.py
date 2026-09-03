import sqlite3

import pandas as pd

from src.config import (
    CLEANED_BILLING_FILE,
    DATABASE_FILE,
)


clean_data = pd.read_csv(
    CLEANED_BILLING_FILE
)

with sqlite3.connect(
    DATABASE_FILE
) as connection:
    clean_data.to_sql(
        "billing",
        connection,
        if_exists="replace",
        index=False,
    )