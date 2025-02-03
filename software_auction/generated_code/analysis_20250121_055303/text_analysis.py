# Analyze the sentiment behind the conversation to understand the implication of the customers' needs on the company.
from textblob import TextBlob

conversation = 'Those customers, if they need a certain product in a big context, that means that the company needs the product. So it's not that simple.'
blob = TextBlob(conversation)
blob.sentiment
