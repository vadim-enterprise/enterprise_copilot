# Perform regression analysis to compare differences between primary and secondary health care institutions
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X, y)
