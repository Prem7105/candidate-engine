"""
Configuration for the candidate ranking system.

All scoring weights, skill definitions, and thresholds live here so
they're easy to tweak without digging through scorer code.
"""

# ---------------------------------------------------------------------------
# Scoring weights — these control how the final score is blended.
# They should sum to 1.0. Tuned based on what the JD emphasizes.
# ---------------------------------------------------------------------------

WEIGHTS = {
    "semantic":          0.40,
    "skill_relevance":   0.20,
    "experience_fit":    0.20,
    "career_trajectory": 0.10,
    "behavioral":        0.05,
    "location_fit":      0.025,
    "education":         0.025,
}


# ---------------------------------------------------------------------------
# Skill definitions — pulled directly from the JD text.
#
# "Must have" skills are the ones the JD says "you absolutely need."
# "Nice to have" are things they'd like but won't reject you for.
# ---------------------------------------------------------------------------

MUST_HAVE_SKILLS = {
    # Embeddings & retrieval
    "embeddings", "sentence-transformers", "retrieval", "semantic search",
    "embedding", "dense retrieval", "bi-encoder", "cross-encoder",
    # Vector DBs / search infra
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
    "elasticsearch", "vector search", "vector database", "hybrid search",
    # Python & Core AI
    "python", "pytorch", "llms", "langchain", "mlops", "aws",
    # Ranking / evaluation
    "ranking", "ndcg", "mrr", "map", "evaluation", "information retrieval",
    "search ranking", "recommendation", "reranking",
}

NICE_TO_HAVE_SKILLS = {
    "lora", "qlora", "peft", "fine-tuning", "finetuning",
    "llm", "large language model", "gpt", "transformer",
    "xgboost", "learning-to-rank", "lightgbm", "catboost",
    "hr-tech", "recruiting", "talent", "marketplace",
    "distributed systems", "kubernetes", "docker", "mlops",
    "open-source", "oss",
    "rag", "retrieval-augmented generation",
    "langchain", "llamaindex",
    "nlp", "natural language processing", "text classification",
    "pytorch", "tensorflow", "huggingface",
    "spark", "airflow", "data engineering", "etl",
    "aws", "gcp", "azure", "cloud",
}

# Skills that are relevant to ML/AI work — used for the "is this person
# actually technical" check vs someone who just listed AI keywords
AI_TECHNICAL_SKILLS = {
    "python", "pytorch", "tensorflow", "scikit-learn", "sklearn",
    "numpy", "pandas", "huggingface", "transformers",
    "nlp", "machine learning", "deep learning", "neural network",
    "embeddings", "faiss", "vector search", "retrieval",
    "recommendation", "ranking", "search", "information retrieval",
    "llm", "gpt", "bert", "fine-tuning", "rag",
    "data science", "ml engineering", "mlops",
    "spark", "airflow", "sql", "data engineering",
    "computer vision", "image classification", "object detection",
    "speech recognition", "natural language processing",
    "statistical modeling", "feature engineering",
    "lora", "qlora", "peft",
    "xgboost", "lightgbm", "catboost", "gradient boosting",
}

# ---------------------------------------------------------------------------
# Titles that suggest real AI/ML/Engineering work vs non-technical roles
# ---------------------------------------------------------------------------

STRONG_FIT_TITLES = {
    "ai engineer", "ml engineer", "machine learning engineer",
    "data scientist", "senior data scientist", "lead data scientist",
    "nlp engineer", "search engineer", "ranking engineer",
    "recommendation engineer", "applied scientist",
    "research engineer", "software engineer", "backend engineer",
    "senior software engineer", "staff engineer",
    "data engineer", "analytics engineer", "platform engineer",
    "senior ai engineer", "senior ml engineer",
    "ml engineer", "junior ml engineer", "senior machine learning engineer",
}

WEAK_FIT_TITLES = {
    "marketing manager", "hr manager", "sales executive",
    "content writer", "graphic designer", "accountant",
    "operations manager", "customer support", "project manager",
    "business analyst", "civil engineer", "mechanical engineer",
}

# ---------------------------------------------------------------------------
# Companies the JD explicitly flags as poor fit when they're the ONLY
# career background. Having worked there + product companies is fine.
# ---------------------------------------------------------------------------

CONSULTING_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "hcl", "tech mahindra", "cts", "mindtree",
    "mphasis", "lti", "ltimindtree", "hexaware", "zensar",
}

PRODUCT_COMPANY_SIGNALS = {
    # Companies generally considered product companies
    "google", "meta", "facebook", "amazon", "microsoft", "apple",
    "netflix", "uber", "airbnb", "stripe", "spotify", "twitter",
    "linkedin", "salesforce", "adobe", "oracle", "sap",
    "flipkart", "swiggy", "zomato", "razorpay", "cred",
    "phonepe", "paytm", "ola", "meesho", "groww", "zerodha",
    "freshworks", "zoho", "postman", "browserstack",
    "atlassian", "slack", "figma", "notion", "datadog",
}

# ---------------------------------------------------------------------------
# Location preferences from the JD
# ---------------------------------------------------------------------------

PREFERRED_LOCATIONS = {"pune", "noida"}
TIER1_INDIA_CITIES = {
    "pune", "noida", "delhi", "new delhi", "delhi ncr", "gurgaon",
    "gurugram", "hyderabad", "mumbai", "bangalore", "bengaluru",
    "chennai", "kolkata",
}

PREFERRED_COUNTRY = "india"

# ---------------------------------------------------------------------------
# Behavioral signal thresholds
# ---------------------------------------------------------------------------

# JD says "sub-30-day notice" is ideal, 30+ day is higher bar
IDEAL_NOTICE_PERIOD = 30
MAX_NOTICE_PERIOD = 90

# How many days of inactivity before we start penalizing
INACTIVITY_THRESHOLD_DAYS = 90
SEVERE_INACTIVITY_DAYS = 180

# Minimum recruiter response rate to be considered "reachable"
MIN_RESPONSE_RATE = 0.10

# Experience range from JD
IDEAL_EXP_MIN = 5.0
IDEAL_EXP_MAX = 9.0
# Extended range where we still give partial credit
ACCEPTABLE_EXP_MIN = 3.0
ACCEPTABLE_EXP_MAX = 14.0

# ---------------------------------------------------------------------------
# Model and retrieval settings
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
FAISS_TOP_K = 1000       # How many to pull from FAISS before detailed scoring and cross-encoding
FINAL_TOP_K = 100        # How many to include in final output
EMBEDDING_BATCH_SIZE = 256
