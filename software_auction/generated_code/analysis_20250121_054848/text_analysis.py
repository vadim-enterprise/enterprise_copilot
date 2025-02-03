# Perform sentiment analysis to determine the emotional tone of the statements.
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

nltk.download('vader_lexicon')
sentiment_analyzer = SentimentIntensityAnalyzer()
text = "Look, he's still hooked up in a 0.15, but maybe he's two sets down. But I do feel like now he has confident body language. And I do feel like at the last 7 minutes, he's walking way slower. And he walked really slow to his death from the last ginger."
sentiment = sentiment_analyzer.polarity_scores(text)
print(sentiment)
