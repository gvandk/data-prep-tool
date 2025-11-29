import sys
from PyQt6.QtWidgets import QApplication
from data_prep_tool.ui.main_window import MainWindow
from data_prep_tool.controllers.main_controller import MainController
from data_prep_tool.transformation.transformation_manager import TransformationManager


def main():
    app = QApplication(sys.argv)

    # Create UI
    window = MainWindow()

    manager = TransformationManager(None)
    # Create controller (connects UI <-> Core)
    controller = MainController(window, manager)


    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()