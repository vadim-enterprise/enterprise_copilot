# Perform regression to understand the difference between healthcare units
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X, y)
