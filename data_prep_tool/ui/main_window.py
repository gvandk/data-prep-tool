from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QWidget, QMenuBar, QLabel, QVBoxLayout, QLineEdit, QPushButton, QStackedLayout
from .table_view import TableView
from .layouts.column_options import ColumnPanel
from .layouts.row_options import RowPanel
from .layouts.general_options import GeneralPanel
from .layouts.intro_options import IntroPanel
from .layouts.cell_options import CellPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Processor App")
        self.resize(800, 600)
        
        #TableView to display CSV
        self.table_view = TableView()

        #Central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_layout = QHBoxLayout()
        central_widget.setLayout(central_layout)

        #Left panel with stacked layout
        self.left_panel = QWidget()
        left_layout = QStackedLayout()
        self.left_panel.setLayout(left_layout)
        
        #Intro panel
        self.intro = IntroPanel()
        left_layout.addWidget(self.intro)

        #General info panel
        self.general_options = GeneralPanel()
        left_layout.addWidget(self.general_options)
        
        #Cell options panel
        self.cell_options = CellPanel()
        left_layout.addWidget(self.cell_options)

        #Column options panel
        self.column_options = ColumnPanel(self.table_view)
        left_layout.addWidget(self.column_options)

        #Row options panel
        self.row_options = RowPanel()
        left_layout.addWidget(self.row_options)
        
        central_layout.addWidget(self.left_panel, stretch=1)
        central_layout.addWidget(self.table_view, stretch=3)

        #Menu bar
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu("&File")
        self.open_action = self.file_menu.addAction("Open CSV")
        self.exit_action = self.file_menu.addAction("Exit")
        self.undo_action = self.file_menu.addAction("Undo")
        self.redo_action = self.file_menu.addAction("Redo")
        
        left_layout.setCurrentWidget(self.intro)

        #Connections
        self.table_view.clicked.connect(self.cell_clicked)
        self.table_view.horizontalHeader().sectionClicked.connect(self.column_clicked)
        self.table_view.verticalHeader().sectionClicked.connect(self.row_clicked)

    def get_csv_file(self):
        """Open file dialog and return selected CSV file path or None."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv)"
        )
        return file_path if file_path else None
    
    # def on_index_edited(self, new_text):
    #     if type(self.index) == int:
    #         self.table_view.model().setHeaderData(self.index, Qt.Orientation.Vertical, new_text)
    #     else:
    #         self.table_view.model().setHeaderData(self.index.column(), Qt.Orientation.Vertical, new_text)

    def cell_clicked(self, index):
        self.left_panel.layout().setCurrentWidget(self.cell_options)
        self.index = index
        column = self.table_view.model().headerData(index.column(), Qt.Orientation.Horizontal)
        self.cell_options.column_rename.set_current_column(index.column(), column)

    def column_clicked(self, index):
        self.left_panel.layout().setCurrentWidget(self.column_options)
        self.index = index

        column = self.table_view.model().headerData(index, Qt.Orientation.Horizontal)   
        self.column_options.column_rename.set_current_column(index, column)
        
        encoding = self.column_options.encoder_options.column_encoding_state.get(index, "None")
        self.column_options.encoder_options.set_current_column(index, encoding)
        

    def row_clicked(self, index):
        self.left_panel.layout().setCurrentWidget(self.row_options)
        self.index = index
        self.row_options.row_index.setText(f"Row Index: {index}")

    def reset_to_general(self):
        self.left_panel.layout().setCurrentWidget(self.general_options)
        self.general_options.row_count_label.setText(self.general_options.row_count_label.text()+str(self.table_view.model().rowCount()))
        self.general_options.column_count_label.setText(self.general_options.column_count_label.text()+str(self.table_view.model().columnCount()))