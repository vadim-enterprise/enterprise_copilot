# Perform linear regression between primary and secondary health care institutions
from sklearn.linear_model import LinearRegression
model = LinearRegression()
X = df[['primary_health_care']]
Y = df['secondary_health_care']
model.fit(X, Y)
