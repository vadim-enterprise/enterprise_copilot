# Analyze the sentiment of the conversation
from textblob import TextBlob\n\ntext = 'I feel like you and James Blake have a pretty good... I don't know how to put it, but you have a pretty good use for each other.'\n\nblob = TextBlob(text)\n\nblob.sentiment
