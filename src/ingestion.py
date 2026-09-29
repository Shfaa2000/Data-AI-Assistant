"""تحميل بيانات Cloud Billing من ملف CSV."""

from pathlib import Path

import pandas as pd


def load_data(file_path: Path) -> pd.DataFrame:

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Billing file was not found: {file_path}"
        )

    data = pd.read_csv(file_path)

    if data.empty:
        raise ValueError(
            "The billing file contains no rows."
        )

    return data