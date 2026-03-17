import pandas as pd
import numpy as np

# Load Data
df = pd.read_csv('data.csv')

# Binning: Year of Birth (Custom)
numeric_vals = pd.to_numeric(df['Year of Birth'], errors='coerce')
binned = pd.cut(numeric_vals, bins=[1970.0, 1981.67, 1993.33, 2005.0])
dummies = pd.get_dummies(binned, prefix='Year of Birth')
dummies = dummies.replace({True: 'True', 1: 'True', False: 'False', 0: 'False'})
df = pd.concat([df, dummies], axis=1)
df.drop(columns=['Year of Birth'], inplace=True)

# Select and order final columns
df = df[['Gender', 'City', 'Year of Birth_(1970.0, 1981.67]', 'Year of Birth_(1981.67, 1993.33]', 'Year of Birth_(1993.33, 2005.0]']]
df = df.reset_index(drop=True)

df.to_csv('output.csv', index=False)