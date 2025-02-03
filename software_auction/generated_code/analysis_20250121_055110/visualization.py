# Plot a histogram to visualize the distribution of sensor readings
import matplotlib.pyplot as plt

plt.hist(readings_array, bins='auto')
plt.title('Histogram of Sensor Readings')
plt.xlabel('Reading')
plt.ylabel('Frequency')
plt.show()
