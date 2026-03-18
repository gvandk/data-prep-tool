Data Preparation Tool is a desktop-oriented utility for cleaning and transforming tabular datasets into a binary matrix for easier analysis. It is designed to make common preprocessing operations easier to perform and reproduce in a practical workflow. All transformations done in the GUI, can be exported as a python script, which includes only the necesarry steps in the correct order to get the desired form. This script can be reused using CLI anytime, making common data transformations more trivial.

This project was created as part of a bachelor thesis at Palacký University Olomouc.

## Usage & Installation

### Install from GitHub
1. Install Python 3.10+.
2. Install the package:
   ```bash
   pip install "git+https://github.com/gvandk/data-prep-tool.git"
   ```
3. Start the app:
   ```bash
   data-prep-tool
   ```

### Run tests
1. Install development/test dependencies:
   ```bash
   pip install -e .[dev]
   ```
2. Run tests:
   ```bash
   pytest
   ```

### Run from source
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python -m data_prep_tool.main
   ```

## Notes / Other

- The app uses a single packaged icon file at `data_prep_tool/app_icon.png`.
- On Windows, a process AppUserModelID is set to improve taskbar icon behavior.
- Tests are intended for repository/development use and are not required for normal end-user installation or usage.