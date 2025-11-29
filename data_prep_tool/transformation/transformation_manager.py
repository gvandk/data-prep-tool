from .transformations import ColumnRenameTransformation, oneHotEncodeTransformation, ColumnReorderTransformation
from PyQt6.QtWidgets import QApplication

class TransformationManager:

    def __init__(self, df):
        self.df = df
        self.pipeline = {}
        self.history = []
        self.redo = []


    def load_dataframe(self, df):
        self.df = df
        self.current_df = df.copy()
        self.pipeline = {}
        self.history = []
        self.redo = []


    def apply_transformations(self):
        self.current_df = self.checkpoint_df.copy()
        for key in list(self.pipeline):
            self.current_df = self.pipeline[key].apply(self.current_df)
        return self.current_df

    def add_rename(self, col_index, new_name):
        
        #key="ColRename_" + str(col_index)
        #self.pipeline[key] = ColumnRenameTransformation(col_index, new_name)
        
        self.history.append(ColumnRenameTransformation(col_index, new_name))
        self.current_df = self.history[-1].apply(self.current_df)
    
    def add_encoding(self, col_index, encoding):
        if encoding != "One-Hot":
            return
        elif encoding == "One-Hot":
            self.history.append(oneHotEncodeTransformation(col_index))
        
        self.current_df = self.history[-1].apply(self.current_df)
        
    #def add_column_reorder(self, new_order):
    #    self.history.append(ColumnReorderTransformation(new_order))
    #    self.current_df = self.history[-1].apply(self.current_df)

    def undo_transformation(self):
        if not self.history:
            QApplication.beep()
            return
        
        #key = list(self.pipeline.keys())[-1]
        #self.pipeline[key] = self.history.pop()

        self.current_df = self.history[-1].undo(self.current_df)
        self.redo.append(self.history.pop())

    def redo_transformation(self):
        if not self.redo:
            QApplication.beep()
            return
        
        transformation = self.redo.pop()
        self.current_df = transformation.apply(self.current_df)
        self.history.append(transformation)

        
