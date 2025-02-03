# Perform text analysis to understand the context of hair loss, treatments, and their effects.
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Tokenize the text
tokens = word_tokenize('I started experiencing hair loss, and I just knew that my part was in the action of that, and that's what worked out for me. I received and rewrote a report of hair from major doctors and treatments, including serums, tubes, and pills, formulating prescription ingredients, and concrete supplements.')

# Remove stopwords
stop_words = set(stopwords.words('english'))
filtered_tokens = [w for w in tokens if not w in stop_words]

# Frequency distribution
freq_dist = nltk.FreqDist(filtered_tokens)

# Print and plot
print(freq_dist.most_common(10))
freq_dist.plot(30)
