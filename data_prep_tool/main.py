import sys
import ctypes
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtGui import QIcon
from .ui.main_window import MainWindow
from .ui.main_controller import MainController
from .core.transformation_manager import TransformationManager
from .core.dataframe_wrapper import DataFrameWrapper


def _resolve_icon_path() -> Path | None:
    candidates = []
    # Handle PyInstaller case where data files are extracted to a temp directory
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.extend([
            meipass / "data_prep_tool" / "app_icon.png",
        ])

    package_dir = Path(__file__).resolve().parent
    candidates.extend([
        package_dir / "app_icon.png",
    ])

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None

def main():
    # Set application user model ID on Windows for proper taskbar grouping and icon display
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("data-prep-tool")
        except Exception:
            pass

    app = QApplication(sys.argv)

    icon_path = _resolve_icon_path()
    icon = app.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
    if icon_path:
        icon = QIcon(str(icon_path))
    app.setWindowIcon(icon)

    # Create Core Components
    wrapper = DataFrameWrapper(None)
    manager = TransformationManager(wrapper)

    # Create UI
    window = MainWindow()
    window.setWindowIcon(icon)

    # Create Controller
    controller = MainController(window, manager)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()