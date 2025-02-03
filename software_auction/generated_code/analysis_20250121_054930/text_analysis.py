# To analyze the sentiment of the conversation
from textblob import TextBlob\n\ntext = 'Whether you want to say it's a vocal layer, he's bluffing a little bit, but he's inserting more than he is, I think he's...'\nblob = TextBlob(text)\nprint(blob.sentiment)


# To extract key phrases to understand the main topics
from nltk import word_tokenize\nfrom gensim import corpora\n\ntokens = word_tokenize(text)\ndictionary = corpora.Dictionary([tokens])\nprint(dictionary.token2id)
