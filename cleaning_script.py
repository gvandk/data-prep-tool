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

df = pd.concat([df, pd.DataFrame([{col: '' for col in df.columns}])]).reset_index(drop=True)
df = df.drop(index=3).reset_index(drop=True)
df = df.drop(index=2).reset_index(drop=True)
# Add column: new_column
df['new_column'] = ''
# Add column: new_column
df['new_column'] = '12'
# Add column: new_columns
df['new_columns'] = '12'
df = pd.concat([df, pd.DataFrame([{col: '12' for col in df.columns}])]).reset_index(drop=True)

# Select and order final columns
df = df[['Year of Birth', 'City', 'new_column', 'new_columns']]
df = df.reset_index(drop=True)

df.to_csv(output_path, index=False)
print(f'Done. Saved to {output_path}')