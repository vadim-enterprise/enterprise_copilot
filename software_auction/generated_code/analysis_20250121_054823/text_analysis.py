# Analyzing the text for rhyme and reason
import nltk\n\n# Tokenize the text\ntokens = nltk.word_tokenize('a lot of rhyme and reason to what it is about, yeah.')\n\n# Perform parts of speech tagging\npos_tags = nltk.pos_tag(tokens)\n\n# Perform named entity recognition\nner = nltk.ne_chunk(pos_tags)
