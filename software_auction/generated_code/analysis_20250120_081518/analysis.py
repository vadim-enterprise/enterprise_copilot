# Perform linear regression
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X, y)


# Validate the model
from sklearn.model_selection import cross_val_score
scores = cross_val_score(model, X, y, cv=5)
