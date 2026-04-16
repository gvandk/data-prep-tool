Data Preparation Tool is a desktop-oriented utility for cleaning and transforming tabular datasets into a binary matrix for easier analysis. It is designed to make common preprocessing operations easier to perform and reproduce in a practical workflow. All transformations done in the GUI, can be exported as a python script, which includes only the necesarry steps in the correct order to get the desired form. This script can be reused using CLI anytime, making common data transformations more trivial.

This project was created as part of a bachelor thesis at Palacký University Olomouc.

## Usage & Installation

### Install from GitHub
1. Install Python 3.10+.
2. Install the package:
   ```bash
   pip install "git+https://github.com/gvandk/data-prep-tool.git"
   ```
3. Run the app:
   ```bash
   data-prep-tool
   ```

### Run from source
1. Clone the repository:
   ```bash
   git clone https://github.com/gvandk/data-prep-tool.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python -m data_prep_tool.main
   ```
   
#### Run tests
1. Navigate into the cloned repository directory:
   ```bash
   cd data-prep-tool
   ```
2. Run the tests:
   ```bash
   pytest
   ```

## Using the generated script

After applying transformations in the GUI, use **File -> Export Script** to save a Python script (default name: `cleaning_script.py`).

The exported script replays your transformation pipeline and can be run from the command line:

```bash
python cleaning_script.py [input_csv] [output_csv]
```

- If `input_csv` is omitted or set to `-`, the script reads CSV data from standard input.
- If `output_csv` is omitted or set to `-`, the script writes the transformed table to standard output.

Examples:

```bash
# Read from a file and save to a file
python cleaning_script.py raw_data.csv cleaned_data.csv

# Read from stdin and write to stdout
cat raw_data.csv | python cleaning_script.py - -

# Read from stdin and save to a file
cat raw_data.csv | python cleaning_script.py - cleaned_data.csv
```

Notes:

- The exported script requires `pandas` in the environment where it is executed.
- On failure, the script prints the transformation step that failed together with a readable reason and exits with a non-zero status.
   
## Notes / Other

- The app uses a single packaged icon file at `data_prep_tool/app_icon.png`.
- On Windows, a process AppUserModelID is set to improve taskbar icon behavior.
- Tests are intended for repository/development use and are not required for normal end-user installation or usage.
