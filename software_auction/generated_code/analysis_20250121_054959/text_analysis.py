# Perform sentiment analysis to understand the emotional tone of the conversation.
from nltk.sentiment.vader import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()
sentiment = sia.polarity_scores('This is exactly what Tommy's navigating. He's got a little more pep in the step considering the way you lost those two sets. You keep telling yourself, I'm thicker than the other guy. I'm putting in the hard yards.')
print(sentiment)


# Extract key phrases to understand the main topics of the conversation.
from rake_nltk import Rake

r = Rake()
r.extract_keywords_from_text('This is exactly what Tommy's navigating. He's got a little more pep in the step considering the way you lost those two sets. You keep telling yourself, I'm thicker than the other guy. I'm putting in the hard yards.')
key_phrases = r.get_ranked_phrases()
print(key_phrases)
