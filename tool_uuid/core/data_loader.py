import pandas as pd
from core.dataframe_wrapper import DataFrameWrapper

def load_csv(file_path: str):
    """Load CSV as pandas DataFrame and wrap it using the wrapper."""
    try:
        df = pd.read_csv(file_path)
        return DataFrameWrapper(df)
    except Exception as e:
        raise RuntimeError(f"Failed to load CSV: {e}")
