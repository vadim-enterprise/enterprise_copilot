# Identify segments of customers based on their interest in finding a good deal
from sklearn.cluster import KMeans

# Assuming 'data' is a pandas DataFrame containing customer data
kmeans = KMeans(n_clusters=3, random_state=0).fit(data[['interest_in_deals']])
data['interest_cluster'] = kmeans.labels_
print(data['interest_cluster'].value_counts())
