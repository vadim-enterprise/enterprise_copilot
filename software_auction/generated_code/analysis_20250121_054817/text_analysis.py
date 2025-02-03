# Sentiment analysis to understand the emotions expressed in the conversation
from nltk.sentiment.vader import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()
sentiment = sia.polarity_scores('Do you feel like the one thing that\'s hurt? Yeah, I did have a couple of goblins. That still hasn\'t come close to you guys, but I feel like there\'s been one thing that\'s hurt Tommy more than anything. His first ball. You know, he\'s been under cue for that for ages of constant first ball mistakes.')


# Text summarization to get a concise summary of the conversation
from gensim.summarize import summarize

summary = summarize('Do you feel like the one thing that\'s hurt? Yeah, I did have a couple of goblins. That still hasn\'t come close to you guys, but I feel like there\'s been one thing that\'s hurt Tommy more than anything. His first ball. You know, he\'s been under cue for that for ages of constant first ball mistakes.')
