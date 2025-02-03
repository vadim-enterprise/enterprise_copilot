# Determine which regression can be used
import seaborn as sns

# Generate a pairplot to visualize relationship between variables
sns.pairplot(df)

# Based on the plot, you can determine the type of regression to be used


# Use linear regression
from sklearn.linear_model import LinearRegression
model = LinearRegression()
model.fit(X, y)


# Use logistic regression
from sklearn.linear_model import LogisticRegression
model = LogisticRegression()
model.fit(X, y)


# Use ridge regression
from sklearn.linear_model import Ridge
model = Ridge()
model.fit(X, y)


# Use lasso regression
from sklearn.linear_model import Lasso
model = Lasso()
model.fit(X, y)
