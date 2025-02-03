# Clean the text by removing punctuations and converting the text into lowercase letters for better sentiment analysis.
import string
text_clean = text.translate(str.maketrans('', '', string.punctuation)).lower()
print(text_clean)
