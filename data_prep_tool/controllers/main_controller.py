from data_prep_tool.core.data_loader import load_csv
from data_prep_tool.models.table_model import DataFrameModel
from data_prep_tool.ui.main_window import MainWindow
from data_prep_tool.transformation.transformation_manager import TransformationManager
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QApplication

class MainController:
    def __init__(self, main_window, transformation_manager):
        self.main_window = main_window
        self.model = DataFrameModel()
        self.main_window.table_view.setModel(self.model)
        self.manager = transformation_manager

        # Connect UI actions
        self.main_window.open_action.triggered.connect(self.open_csv)
        self.main_window.exit_action.triggered.connect(self.main_window.close)
        self.main_window.undo_action.triggered.connect(self.undo)
        self.main_window.redo_action.triggered.connect(self.redo)
        self.main_window.cell_options.column_rename_request.connect(self.rename_request)
        self.main_window.column_options.column_rename_request.connect(self.rename_request)
        self.main_window.column_options.column_encoding_request.connect(self.encoding_request)

        #self.main_window.table_view.columnReorderRequested.connect(self.column_reorder_request)

        
        self.main_window.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        #self.main_window.undo_action.triggered.connect(self.undo)

        self.main_window.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        #self.main_window.redo_action.triggered.connect(self.redo)

    def open_csv(self):
        file_path = self.main_window.get_csv_file()
        if file_path:
            df = load_csv(file_path)
            self.model.setDataFrame(df)
            MainWindow.reset_to_general(self.main_window)
            self.manager.load_dataframe(df)
    
    def rename_request(self, column, new_name):
        self.manager.add_rename(column, new_name)
        self.refresh_view()
    
    def encoding_request(self, column, encoding):
        self.manager.add_encoding(column, encoding)
        self.refresh_view()

    def refresh_view(self):
        transformed_df = self.manager.current_df
        self.model.setDataFrame(transformed_df)

    #def column_reorder_request(self, new_order):
    #    self.manager.add_column_reorder(new_order)


    def undo(self):
        self.manager.undo_transformation()
        self.refresh_view()
    
    def redo(self):
        self.manager.redo_transformation()
        self.refresh_view()
