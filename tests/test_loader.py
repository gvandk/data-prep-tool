import pytest
from data_prep_tool.core.data_loader import load_csv
import pandas as pd
import os


def test_load_csv(tmp_path):
    test_file = tmp_path / "test.csv"
    test_file.write_text("a,b,c\n1,2,3\n4,5,6")

    df = load_csv(str(test_file))
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 3)
