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

# One-Hot Encode: Gender
dummies = pd.get_dummies(pd.Categorical(df['Gender'], categories=list(pd.unique(df['Gender']))), prefix='Gender')
dummies = dummies.replace({True: 't', 1: 't', False: 'F', 0: 'F'})
df = pd.concat([df, dummies], axis=1)
# One-Hot Encode: City
dummies = pd.get_dummies(pd.Categorical(df['City'], categories=list(pd.unique(df['City']))), prefix='City')
dummies = dummies.replace({True: 't', 1: 't', False: 'F', 0: 'F'})
df = pd.concat([df, dummies], axis=1)
df.rename(columns={'City_Prague': 'City_P'rague'}, inplace=True)
df.rename(columns={'City_Los Angeles': 'City_LA'}, inplace=True)
# Binning & Binarization: Year of Birth (Equal Width)
bins = pd.cut(df['Year of Birth'], bins=5)
dummies = pd.get_dummies(bins, prefix='Year of Birth')
dummies = dummies.replace({True: 't', 1: 't', False: 'F', 0: 'F'})
df = pd.concat([df, dummies], axis=1)
df.drop(columns=['Year of Birth'], inplace=True)

df = df[['Gender_Did not define', 'Gender_Male', 'City_P'rague', 'Gender_Female', 'City_Tokyo', 'City_Rome', 'City_New York', 'City_Barcelona', 'City_Warsaw', 'City_London', 'City_Stockholm', 'City_Sydney', 'City_LA', 'City_Madrid', 'City_Paris', 'City_Vienna', 'City_Berlin', 'City_Chicago', 'City_Seoul', 'City_Munich', 'City_Toronto', 'City_Amsterdam', 'Year of Birth_(1969.965, 1977.0]', 'Year of Birth_(1977.0, 1984.0]', 'Year of Birth_(1984.0, 1991.0]', 'Year of Birth_(1991.0, 1998.0]', 'Year of Birth_(1998.0, 2005.0]']]

df.to_csv(output_path, index=False)
print(f'Done. Saved to {output_path}')