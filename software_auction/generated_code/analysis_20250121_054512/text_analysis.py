# Analyze the text to understand the sentiments and topics discussed.
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()

feedback_text = 'We mentioned this earlier, we wanted to make sure the feedback was not falling to the board. We had a board meeting with KC, but they didn't know who to go to. It wasn't long, it was less than 15 minutes. Of course, you're right, it wasn't time to have more fans.'

sentiment = sia.polarity_scores(feedback_text)
print('Sentiment:', sentiment)
