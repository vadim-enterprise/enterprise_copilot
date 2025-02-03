# Statistical analysis of the scoring pattern
import pandas as pd

# Assuming score_data is a DataFrame with scores
score_data['Sparrow_lead'] = score_data['Sparrow'] - score_data['Opponent']
score_data['Sparrow_lead'].describe()
