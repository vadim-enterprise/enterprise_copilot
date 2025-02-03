# Analyze the sentiment of the conversation to understand the tone (positive, negative, neutral)
from nltk.sentiment.vader import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()
sentiment = sia.polarity_scores('we find out a second or third way so when you're down with two sets you know you're just looking for a feed a break')
print(sentiment)


# Perform text preprocessing such as tokenization, removal of stop words, and lemmatization to prepare the text for further analysis
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

stop_words = set(stopwords.words('english'))
word_tokens = word_tokenize('we find out a second or third way so when you're down with two sets you know you're just looking for a feed a break')
filtered_sentence = [w for w in word_tokens if not w in stop_words]

lemmatizer = WordNetLemmatizer()
lemmatized_output = ' '.join([lemmatizer.lemmatize(w) for w in filtered_sentence])
print(lemmatized_output)
