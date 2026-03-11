from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
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
        self.left_layout = QStackedLayout()
        self.left_panel.setLayout(self.left_layout)
        
        #Intro panel
        self.intro = IntroPanel()
        self.left_layout.addWidget(self.intro)

        #General info panel
        self.general_options = GeneralPanel()
        self.left_layout.addWidget(self.general_options)
        
        #Cell options panel
        self.cell_options = CellPanel()
        self.left_layout.addWidget(self.cell_options)

        #Column options panel
        self.column_options = ColumnPanel()
        self.left_layout.addWidget(self.column_options)

        #Row options panel
        self.row_options = RowPanel()
        self.left_layout.addWidget(self.row_options)
        
        central_layout.addWidget(self.left_panel, stretch=1)
        central_layout.addWidget(self.table_view, stretch=3)

        #Menu bar
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu("&File")
        self.action_load = self.file_menu.addAction("Load CSV")
        self.action_export = self.file_menu.addAction("Export CSV Script")
        self.action_exit = self.file_menu.addAction("Exit")

        self.edit_menu = self.menu_bar.addMenu("&Edit")
        self.action_undo = self.edit_menu.addAction("Undo")
        self.action_redo = self.edit_menu.addAction("Redo")
        
        # Shortcuts
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        
        self.set_panel("intro")
    
    def set_panel(self, panel_name: str):
        """Helper to switch panels by name."""
        mapping = {
            "intro": self.intro,
            "general": self.general_options,
            "cell": self.cell_options,
            "column": self.column_options,
            "row": self.row_options
        }
        widget = mapping.get(panel_name)
        if widget:
            self.left_layout.setCurrentWidget(widget)