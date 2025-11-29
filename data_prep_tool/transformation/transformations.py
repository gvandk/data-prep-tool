from .base_transformation import BaseTransformation
import pandas as pd

class ColumnRenameTransformation(BaseTransformation):

    def __init__(self, col_index, new_name):
        self.col_index = col_index
        self.new_name = new_name

    def apply(self, df):
        df = df.copy()
        self.old_name =  df.columns.values[self.col_index]
        df.columns.values[self.col_index] = self.new_name
        return df
    
    def to_script(self):
        return f'df.columns.values[{self.col_index}] = "{self.new_name}"'
    
    def undo(self, df):
        df = df.copy()
        df.columns.values[self.col_index] = self.old_name
        return df
    
class oneHotEncodeTransformation(BaseTransformation):
    def __init__(self, col_index):
        self.col_index = col_index
        self.column = None
        self.dummies = None
        self.values = None

    def apply(self, df):
        df = df.copy()
        self.column = df.columns.values[self.col_index]
        print(self.column, flush=True)
        self.values = df[self.column].copy()
        self.dummies = pd.get_dummies(df[self.column], prefix=self.column)
        df = pd.concat([df.drop(columns=[self.column]), self.dummies], axis=1)
        return df

    def to_script(self):
        return f'df = pd.concat([df.drop(columns=["{self.column}"]), pd.get_dummies(df["{self.column}"], prefix="{self.column}")], axis=1)'

    def undo(self, df):
        df = df.copy()
        df = df.drop(columns=self.dummies.columns)
        new_order = list(df.columns)[:self.col_index] + [self.column] + list(df.columns)[self.col_index:]
        print(new_order, flush=True)
        df[self.column] = self.values
        df = df.reindex(columns=new_order)
        return df
    
class ColumnReorderTransformation(BaseTransformation):
    def __init__(self, new_order):
        self.new_order = new_order
        self.old_order = None

    def apply(self, df):
        df = df.copy()
        self.old_order = df.columns.tolist()
        df = df[self.new_order]
        return df

    def undo(self, df):
        df = df.copy()
        df = df[self.old_order]
        return df

    def to_script(self):
        new_order_str = ", ".join(f'"{col}"' for col in self.new_order)
        return f'df = df[[{new_order_str}]]'
