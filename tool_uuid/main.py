import sys
from PyQt6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .ui.main_controller import MainController
from .core.transformation_manager import TransformationManager
from .core.dataframe_wrapper import DataFrameWrapper

def main():
    app = QApplication(sys.argv)

    # 1. Create Core Components
    wrapper = DataFrameWrapper(None)
    manager = TransformationManager(wrapper)

    # 2. Create UI
    window = MainWindow()

    # 3. Create Controller
    controller = MainController(window, manager)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()