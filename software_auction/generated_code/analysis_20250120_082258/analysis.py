# Perform linear optimization
from scipy.optimize import linprog

# Define the coefficients of the inequalities
# Here, the coefficients are placeholders as 'c', 'A_ub', 'b_ub'
c = [-1, 4]
A = [[-3, 1], [1, 2]]
b = [6, 4]

# Perform linear optimization
x_bounds = (None, None)
res = linprog(c, A_ub=A, b_ub=b, bounds=x_bounds, method='highs')
