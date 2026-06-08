import pandas as pd
import sqlite3

# Load the CSV file into a DataFrame
df = pd.read_csv("HRDataset_v14.csv")

# Connect to SQLite (creates the file if it doesn't exist)
conn = sqlite3.connect("hr_data.db")

# Export the data into an SQLite table
df.to_sql("target_table_name", conn, if_exists="replace", index=False)
conn.close()
