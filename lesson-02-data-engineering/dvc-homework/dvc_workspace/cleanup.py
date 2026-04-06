import pandas as pd

df = pd.read_csv('data/dataset.csv')

df = df.drop_duplicates(subset=['id'])

df = df.dropna()

df['category'] = df['category'].str.lower()

df.loc[df['name'] == 'Bob', 'category'] = 'enterprise'

df.loc[df['name'] == 'Hank', 'value'] = 4800

df.to_csv('data/dataset.csv', index=False)