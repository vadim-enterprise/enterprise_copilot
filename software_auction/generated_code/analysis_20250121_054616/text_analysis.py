# Perform sentiment analysis to understand the emotional tone of the text.
from textblob import TextBlob

# The text to analyze
sentences = 'Generate contextually appropriate analysis instructions from this conversation: being made good and gathered for you. Helping you stay unsparkled waters and taste your love. Made with natural flavors and fantastic combinations. Delicious salads, chopped and ready for four easy meals.'

# Create a TextBlob object
blob = TextBlob(sentences)

# Perform sentiment analysis
sentiment = blob.sentiment

# Print the sentiment
print('Sentiment: ', sentiment)


# Perform keyword extraction to identify important words in the text.
from sklearn.feature_extraction.text import CountVectorizer

# The text to analyze
sentences = ['Generate contextually appropriate analysis instructions from this conversation: being made good and gathered for you. Helping you stay unsparkled waters and taste your love. Made with natural flavors and fantastic combinations. Delicious salads, chopped and ready for four easy meals.']

# Create the CountVectorizer object
vectorizer = CountVectorizer()

# Perform keyword extraction
X = vectorizer.fit_transform(sentences)

# Get the feature names
feature_names = vectorizer.get_feature_names_out()

# Print the keywords
print('Keywords: ', feature_names)
