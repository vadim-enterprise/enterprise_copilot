# Plotting the number of points in different sets
import matplotlib.pyplot as plt

plt.figure(figsize=(10,7))
plt.plot(['Set1', 'Set2', 'Set3'], [set1_points.mean(), set2_points.mean(), set3_points.mean()])
plt.xlabel('Set')
plt.ylabel('Points')
plt.title('Number of points in different sets')
plt.show()
