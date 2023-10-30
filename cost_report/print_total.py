import os
import pandas as pd

# Get a list of all Excel files in the current directory
excel_files = [file for file in os.listdir() if file.endswith(".xlsx")]

# Initialize a variable to store the total cost
total_cost = 0

# Iterate through the Excel files and sum the 'lineItem/UnblendedCost' column
for file in excel_files:
    try:
        df = pd.read_excel(file)
        total_cost += df['lineItem/UnblendedCost'].sum()
    except Exception as e:
        print(f"Error reading {file}: {e}")

# Print the total cost
print("Total Unblended Cost from all Excel files:", total_cost)
