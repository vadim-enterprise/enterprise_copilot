# Perform Lasso regression
from sklearn.linear_model import Lasso
model = Lasso()
model.fit(X, y)
