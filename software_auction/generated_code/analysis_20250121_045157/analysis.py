# Perform linear regression
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X, y)


# Perform logistic regression
from sklearn.linear_model import LogisticRegression
model = LogisticRegression()
model.fit(X, y)


# Perform ridge regression
from sklearn.linear_model import Ridge
model = Ridge(alpha=1.0)
model.fit(X, y)


# Perform lasso regression
from sklearn.linear_model import Lasso
model = Lasso(alpha=0.1)
model.fit(X, y)
