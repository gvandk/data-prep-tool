import pandas as pd


def load_csv(file_path: str):
    """Load CSV file into a pandas DataFrame."""
    try:
        df = pd.read_csv(file_path)
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load CSV: {e}")
