import pandas as pd
import numpy as np
import sys
import os

if len(sys.argv) != 3:
    print('Usage: python cleaning_script.py <source_csv> <output_csv>')
    sys.exit(1)

source_path = sys.argv[1]
output_path = sys.argv[2]

if not os.path.exists(source_path):
    print(f'Error: Source file {source_path} not found.')
    sys.exit(1)

# Load Data
df = pd.read_csv(source_path)

# Rename Gender -> G"ender
df.rename(columns={'Gender': 'G"ender'}, inplace=True)
df.at[0, 'G"ender'] = 'Did no"t def\'ine'
df.at[1, 'G"ender'] = 'M"al\'easdasdsad'

df = df[['G"ender', 'Year of Birth', 'City']]

df.to_csv(output_path, index=False)
print(f'Done. Saved to {output_path}')