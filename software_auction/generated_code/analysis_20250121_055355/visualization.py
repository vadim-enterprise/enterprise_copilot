# Visualize the distribution of interest levels among potential customers
import matplotlib.pyplot as plt

# Assuming 'data' is a pandas DataFrame containing customer data
data['interest_in_deals'].hist()
plt.title('Distribution of Interest in Deals')
plt.xlabel('Interest Level')
plt.ylabel('Number of Customers')
plt.show()
