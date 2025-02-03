# Analyzing the correlation between the positioning and the number of points
positioning_points_correlation = data[['positioning', 'points']].corr()
print(positioning_points_correlation)
