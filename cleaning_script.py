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

# Add column: new_column
df['new_column'] = '1'

# Select and order final columns
df = df[['Gender', 'City', 'new_column', 'Year of Birth']]
df = df.reset_index(drop=True)

# Cell edits
df.at[98, 'new_column'] = 'ba'
df.at[98, 'Year of Birth'] = '15'
df.at[99, 'Year of Birth'] = '1'

# Row operations
df = pd.concat([df, pd.DataFrame([{col: '' for col in df.columns}])]).reset_index(drop=True)
df = pd.concat([df, pd.DataFrame([{col: '1' for col in df.columns}])]).reset_index(drop=True)
df = df.drop(index=98).reset_index(drop=True)
df = df.drop(index=95).reset_index(drop=True)

df.to_csv(output_path, index=False)
print(f'Done. Saved to {output_path}')