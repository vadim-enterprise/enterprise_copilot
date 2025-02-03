# Sentiment analysis to understand the sentiment behind the statement.
from nltk.sentiment.vader import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()

statement = 'Two years of poverty compared to four years of Notre Dame, I'm sad I can't compete.'

sentiment = sia.polarity_scores(statement)

print(sentiment)
