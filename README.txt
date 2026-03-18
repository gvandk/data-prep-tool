Data Prep Tool

Install from GitHub (recommended)
1. Install Python 3.10+.
2. Run:
	pip install "git+https://github.com/gvandk/data-prep-tool.git"
3. Start the app:
	data-prep-tool

Run from source
1. Clone the repository.
2. Install dependencies:
	pip install -r requirements.txt
3. Run:
	python -m data_prep_tool.main

Run tests
1. Install test dependencies:
	pip install -e .[dev]
2. Run:
	pytest

Create a standalone executable with PyInstaller
1. Install PyInstaller:
	pip install pyinstaller
2. Build (Windows):
	pyinstaller --noconfirm --windowed --name data-prep-tool --icon data_prep_tool/app_icon.png --add-data "data_prep_tool/app_icon.png;data_prep_tool" -m data_prep_tool.main
3. Build (Linux/macOS):
	pyinstaller --noconfirm --windowed --name data-prep-tool --icon data_prep_tool/app_icon.png --add-data "data_prep_tool/app_icon.png:data_prep_tool" -m data_prep_tool.main

Notes
- The app uses a single packaged icon file at `data_prep_tool/app_icon.png`.
- On Windows, a process AppUserModelID is set to improve taskbar icon behavior. 
- Tests are intended for repository/development use and are not required for normal end-user installation or usage.
