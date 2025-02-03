# Analyzing the text for sentiment and key phrases
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize

# text
sentences = ['These berries come in a peak ripeness, with a good everyday scent.', 'Everyday fragrance and maple fragrances can be made for you, gathered for you.']

# sentiment analysis
analyzer = SentimentIntensityAnalyzer()
for sentence in sentences:
    sentiment = analyzer.polarity_scores(sentence)
    print(sentence, '\n', sentiment, '\n')

# key phrase extraction
from gensim.summarize import keywords
for sentence in sentences:
    print(keywords(sentence, words=5))
