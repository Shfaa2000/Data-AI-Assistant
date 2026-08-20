import pandas as pd
from pathlib import Path


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Billing file not found: {path}")

    return pd.read_csv(path)