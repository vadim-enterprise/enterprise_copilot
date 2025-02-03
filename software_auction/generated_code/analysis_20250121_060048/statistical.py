# Comparison of points in different sets
import pandas as pd

# Assuming 'data' is a DataFrame containing the points data
set1_points = data['set1']
set2_points = data['set2']
set3_points = data['set3']

points_comparison = pd.DataFrame({'Set1': set1_points, 'Set2': set2_points, 'Set3': set3_points})
points_comparison.describe()
