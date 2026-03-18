from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QLabel, QStackedLayout, QScrollArea
from .table_view import TableView
from .layouts.column_options import ColumnPanel
from .layouts.row_options import RowPanel
from .layouts.general_options import GeneralPanel
from .layouts.intro_options import IntroPanel
from .layouts.cell_options import CellPanel

class MainWindow(QMainWindow):
    """Main application window that manages the overall layout and interactions."""
    csv_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Data Preparation Tool")
        self.resize(1100, 700)
        self.setAcceptDrops(True)
        
        # TableView to display CSV
        self.table_view = TableView()

        # Central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_layout = QHBoxLayout()
        central_widget.setLayout(central_layout)

        # Left panel with stacked layout
        self.left_panel = QWidget()
        self.left_layout = QStackedLayout()
        self.left_panel.setLayout(self.left_layout)

        self.left_scroll_area = QScrollArea()
        self.left_scroll_area.setWidgetResizable(True)
        self.left_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.left_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.left_scroll_area.setMinimumWidth(360)
        self.left_scroll_area.setMaximumWidth(420)
        self.left_scroll_area.setWidget(self.left_panel)
        
        # Intro panel
        self.intro = IntroPanel()
        self.left_layout.addWidget(self.intro)

        # General info panel
        self.general_options = GeneralPanel()
        self.left_layout.addWidget(self.general_options)
        
        # Cell options panel
        self.cell_options = CellPanel()
        self.left_layout.addWidget(self.cell_options)

        # Column options panel
        self.column_options = ColumnPanel()
        self.left_layout.addWidget(self.column_options)

        # Row options panel
        self.row_options = RowPanel()
        self.left_layout.addWidget(self.row_options)
        
        # Right panel with placeholder and table view
        self.table_placeholder = QLabel("Load a CSV file or drag and drop it here")
        self.table_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_placeholder.setWordWrap(True)

        self.table_panel = QWidget()
        self.table_layout = QStackedLayout()
        self.table_panel.setLayout(self.table_layout)
        self.table_layout.addWidget(self.table_placeholder)
        self.table_layout.addWidget(self.table_view)

        central_layout.addWidget(self.left_scroll_area, stretch=1)
        central_layout.addWidget(self.table_panel, stretch=3)

        # Menu bar
        self.menu_bar = self.menuBar()
        self.file_menu = self.menu_bar.addMenu("&File")
        self.action_load = self.file_menu.addAction("Load CSV")
        self.action_export = self.file_menu.addAction("Export Script")
        self.action_export_csv = self.file_menu.addAction("Export CSV")
        self.action_exit = self.file_menu.addAction("Exit")

        self.edit_menu = self.menu_bar.addMenu("&Edit")
        self.action_undo = self.edit_menu.addAction("Undo")
        self.action_redo = self.edit_menu.addAction("Redo")
        self.edit_menu.addSeparator()
        self.action_delete = self.edit_menu.addAction("Delete")
        
        # Shortcuts
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_delete.setShortcut(QKeySequence.StandardKey.Delete)
        
        self.set_panel("intro")
        self.show_table_placeholder(True)
    
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

    def show_table_placeholder(self, show: bool):
        if show:
            self.table_layout.setCurrentWidget(self.table_placeholder)
        else:
            self.table_layout.setCurrentWidget(self.table_view)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path and local_path.lower().endswith(".csv"):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path and local_path.lower().endswith(".csv"):
                self.csv_dropped.emit(local_path)
                event.acceptProposedAction()
                return
        event.ignore()