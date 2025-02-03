# Cleaning and preparation of the project data for further analysis
import pandas as pd

# Assuming the project data is in a csv file
project_data = pd.read_csv('project_data.csv')

# Show the first few rows of the data
print(project_data.head())

# Describe the data
print(project_data.describe())

# Check for missing values
print(project_data.isnull().sum())
