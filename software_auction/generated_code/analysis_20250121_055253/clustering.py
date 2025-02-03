# Segmentation of existing customers to find potential customers in similar segments
from sklearn.cluster import KMeans\n\n# Assume `data` is your DataFrame and you've already preprocessed it\nkmeans = KMeans(n_clusters=5, random_state=0).fit(data)\n\n# Get cluster labels\nlabels = kmeans.labels_\n\n# Add labels to data\ndata['cluster'] = labels
