import sys
from PyQt6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .ui.main_controller import MainController
from .core.transformation_manager import TransformationManager
from .core.dataframe_wrapper import DataFrameWrapper
from .core.data_loader import load_csv

def main():
    app = QApplication(sys.argv)

    # 1. Create Core Components
    # Start with empty wrapper
    wrapper = DataFrameWrapper(None)
    manager = TransformationManager(wrapper)

    # 2. Create UI
    window = MainWindow()

    # 3. Create Controller (Wires them together)
    controller = MainController(window, manager, load_csv)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()