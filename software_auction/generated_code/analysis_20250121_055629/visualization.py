# Plotting the three points on a graph for visual understanding
import matplotlib.pyplot as plt

points = [(x1, y1), (x2, y2), (x3, y3)] # replace with actual points

x_values = [point[0] for point in points]
y_values = [point[1] for point in points]

plt.scatter(x_values, y_values)
plt.show()
