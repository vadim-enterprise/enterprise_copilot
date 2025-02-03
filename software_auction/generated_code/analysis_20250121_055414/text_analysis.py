# Analyze the sentiment of the conversation
from nltk.sentiment import SentimentIntensityAnalyzer

sia = SentimentIntensityAnalyzer()
sentiment = sia.polarity_scores('Do you ever walk into a woman and hurt her? I saw her, I was so very comfortable with her. Why did you lay her down? I was 7. Why did you lay her down? She lost her teeth, right?')
print(sentiment)


# Identify the entities in the conversation
import spacy

nlp = spacy.load('en_core_web_sm')
doc = nlp('Do you ever walk into a woman and hurt her? I saw her, I was so very comfortable with her. Why did you lay her down? I was 7. Why did you lay her down? She lost her teeth, right?')
for ent in doc.ents:
    print(ent.text, ent.start_char, ent.end_char, ent.label_)
