# Calculating the mean and standard deviation of the points for understanding their distribution
import numpy as np

points = [(x1, y1), (x2, y2), (x3, y3)] # replace with actual points

x_values = [point[0] for point in points]
y_values = [point[1] for point in points]

x_mean = np.mean(x_values)
x_std = np.std(x_values)
y_mean = np.mean(y_values)
y_std = np.std(y_values)
