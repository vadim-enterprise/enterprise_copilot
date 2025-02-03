# Visualizing the lead of Sparrow over time
import matplotlib.pyplot as plt

plt.plot(score_data.index, score_data['Sparrow_lead'])
plt.ylabel('Sparrow lead')
plt.show()
