from .base_transformation import BaseTransformation
from data_prep_tool.core.dataframe_wrapper import DataFrameWrapper
import pandas as pd

class RowDeleteTransformation(BaseTransformation):
    """Transformation for deleting a row."""
    def __init__(self, row_index: int | list[int]):
        if isinstance(row_index, list):
            normalized = sorted(set(int(index) for index in row_index))
        else:
            normalized = [int(row_index)]

        if not normalized:
            raise ValueError("At least one row index must be provided.")

        self.row_indices = normalized
        self.row_index = normalized[0]
        self.deleted_rows: list[tuple[int, pd.Series]] = []

    def apply(self, df_wrapper: DataFrameWrapper):
        row_count = len(df_wrapper.df)
        for row_index in self.row_indices:
            if row_index < 0 or row_index >= row_count:
                raise IndexError(f"Row index out of range: {row_index}")

        self.deleted_rows = [
            (row_index, df_wrapper.df.iloc[row_index].copy())
            for row_index in self.row_indices
        ]

        df_wrapper.df = df_wrapper.df.drop(index=self.row_indices).reset_index(drop=True)
        return df_wrapper

    def undo(self, df_wrapper: DataFrameWrapper):
        restored_df = df_wrapper.df
        for row_index, deleted_row in self.deleted_rows:
            top = restored_df.iloc[:row_index]
            bottom = restored_df.iloc[row_index:]
            restored_df = pd.concat([top, deleted_row.to_frame().T, bottom], ignore_index=True)

        df_wrapper.df = restored_df.reset_index(drop=True)
        return df_wrapper