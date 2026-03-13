import pandas as pd
from PyQt6.QtCore import Qt

from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
from data_prep_tool.models.table_model import DataFrameModel


def test_default_max_rows_limit_is_applied():
    df = pd.DataFrame({"A": list(range(1500))})
    wrapper = DataFrameWrapper(df)
    model = DataFrameModel(wrapper)

    assert model.rowCount() == 1000


def test_updating_max_rows_changes_visible_row_count():
    df = pd.DataFrame({"A": list(range(1500))})
    wrapper = DataFrameWrapper(df)
    model = DataFrameModel(wrapper)

    model.set_view_settings(250, 4)

    assert model.rowCount() == 250


def test_float_display_precision_updates_from_view_settings():
    df = pd.DataFrame({"A": [1.234567]})
    wrapper = DataFrameWrapper(df)
    model = DataFrameModel(wrapper)
    index = model.index(0, 0)

    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "1.23"

    model.set_view_settings(1000, 4)

    assert model.data(index, Qt.ItemDataRole.DisplayRole) == "1.2346"
