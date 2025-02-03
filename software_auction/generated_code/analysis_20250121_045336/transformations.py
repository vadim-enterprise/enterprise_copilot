# Split the data into two sets
from sklearn.model_selection import train_test_split
train_set, test_set = train_test_split(df, test_size=0.5)
