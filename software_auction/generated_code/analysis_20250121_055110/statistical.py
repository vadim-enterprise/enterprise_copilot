# Calculate basic statistics such as mean, median and standard deviation
import numpy as np

readings_array = np.array(sensor_readings)

mean = np.mean(readings_array)
median = np.median(readings_array)
std_dev = np.std(readings_array)
