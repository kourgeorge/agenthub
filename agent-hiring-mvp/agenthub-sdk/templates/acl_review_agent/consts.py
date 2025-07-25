# Constants for ACL Review Agent

# OpenAI API defaults
OPENAI_DEFAULT_MODEL = "gpt-4"
OPENAI_DEFAULT_MAX_TOKENS = 800
OPENAI_DEFAULT_TEMPERATURE = 0.3

# Token and character limits
MAX_PAPER_SUMMARY_CHARS = 1000
MAX_SECTION_CHARS = 20000
MAX_BEST_PAPER_JUSTIFICATION_CHARS = 500
MAX_CITED_PAPERS_CONTENT_CHARS = 8000

# Literature review
DEFAULT_REVIEW_DEPTH = 4
MIN_REVIEW_DEPTH = 1
MAX_REVIEW_DEPTH = 1 #5
LITERATURE_QUERIES_PER_DEPTH = 3
MAX_SIMILAR_PAPERS = 2 # 10
MAX_OPENREVIEW_REVIEWS = 2 #5
# Number of rounds for literature review search queries
LITERATURE_QUERY_ROUNDS = 1 #3

# Ratings scales
CONFIDENCE_MIN = 1
CONFIDENCE_MAX = 5
SOUNDNESS_MIN = 1
SOUNDNESS_MAX = 5
OVERALL_ASSESSMENT_MIN = 0
OVERALL_ASSESSMENT_MAX = 5

# Novelty calculation
NOVELTY_MIN = 0.0
NOVELTY_MAX = 1.0
NOVELTY_DEFAULT = 0.5

# Similarity threshold for duplicate papers
TITLE_SIMILARITY_THRESHOLD = 0.8

# TF-IDF fallback
FALLBACK_TOP_WORDS = 10
FALLBACK_WORD_MIN_LENGTH = 4

# Miscellaneous
MAX_TFIDF_TEXTS = 2
MAX_TFIDF_FEATURES = 1000 
