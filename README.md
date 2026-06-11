# Candidate Ranking System — Redrob AI Hackathon

A semantic candidate-JD matching and ranking system built for the "Intelligent Candidate Discovery & Ranking Challenge" (India Runs by Redrob AI).

Given a job description for **Senior AI Engineer** and a pool of **100,000 candidate profiles**, the system identifies and ranks the top 100 best-fit candidates with per-candidate explanations.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Pre-compute embeddings (one-time, takes ~10-20 min on CPU)
python precompute.py --candidates ./path/to/candidates.jsonl --output ./models

# 3. Run the ranker (under 5 minutes)
python rank.py --candidates ./path/to/candidates.jsonl --out ./outputs/submission.csv

# 4. (Optional) Launch the demo UI
streamlit run app.py

# 5. (Optional) Generate the presentation
python reports/deck.py
```

## Project Structure

```
├── rank.py              # Main entry point — produces submission CSV
├── precompute.py        # One-time embedding + FAISS index generation
├── app.py               # Streamlit demo UI
├── requirements.txt     # Python dependencies
├── data/
│   └── jd.json          # Structured job description
├── src/
│   ├── config.py        # Scoring weights, skill lists, thresholds
│   ├── loader.py        # JSONL data loading
│   ├── cleaner.py       # Text normalization, skill standardization
│   ├── honeypot.py      # Honeypot detection logic
│   ├── embeddings.py    # Sentence-transformers + FAISS
│   ├── scorer.py        # All scoring components (6 scorers)
│   ├── ranker.py        # Ranking orchestration + explanation generation
│   └── exporter.py      # CSV export and validation
├── models/              # Cached embeddings + FAISS index
├── outputs/             # Generated submission files
└── reports/
    └── deck.py          # Presentation generator
```

## How It Works

### Architecture

The system uses a two-stage pipeline:

**Stage 0 — Pre-computation** (runs once, can take >5 min):
1. Load all 100K candidates from JSONL
2. Build a text representation for each candidate (headline + summary + career descriptions + skills)
3. Generate 384-dimensional embeddings using `all-MiniLM-L6-v2`
4. Build a FAISS index for fast similarity search
5. Save everything to disk

**Stage 1 — Ranking** (must complete in ≤5 min):
1. Load precomputed artifacts
2. Encode the JD as a query embedding
3. Retrieve top 500 candidates by cosine similarity (FAISS)
4. Detect and exclude honeypot candidates
5. Score each candidate on 7 dimensions
6. Weighted combination → final score
7. Take top 100, generate reasoning, export CSV

### How Candidates Are Ranked

The final score is a weighted blend of 7 scoring dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| Semantic Similarity | 25% | Cosine similarity between candidate profile embedding and JD embedding |
| Skill Relevance | 20% | Must-have vs nice-to-have skill matching, with trust multiplier based on proficiency + duration |
| Experience Fit | 15% | Gaussian centered on 5-9 year range from JD |
| Career Trajectory | 15% | Product company vs consulting, title relevance, job stability, production signals |
| Behavioral Signals | 15% | Response rate, recency, notice period, open-to-work, GitHub activity, verification |
| Location | 5% | India preferred, Pune/Noida bonus, relocation willingness |
| Education | 5% | Field relevance (CS/ML), institution tier, degree level |

### Why This Works Better Than Keyword Matching

1. **Semantic understanding**: A candidate who describes "building a recommendation engine using dense vectors" matches the JD's requirement for "embeddings-based retrieval systems" — even though they share no keywords.

2. **Anti-gaming**: The dataset intentionally contains keyword-stuffer traps. A Marketing Manager who lists 9 AI keywords as skills will score low because:
   - Their career descriptions don't mention technical work
   - Their title history is non-technical
   - Skill proficiency × duration trust scores are low

3. **Behavioral signals**: A technically perfect candidate who hasn't logged in for 6 months and has a 5% recruiter response rate is, for practical hiring, not available. We weight this accordingly.

4. **Honeypot detection**: ~80 candidates have subtly impossible profiles (expert in 10 skills with 0 months experience, career durations that don't match dates). We detect and exclude these.

5. **Career trajectory analysis**: The JD explicitly says consulting-only careers (TCS, Infosys, Wipro) are a poor fit. We check the mix of product vs consulting companies in career history.

## Configuration

All scoring weights, skill definitions, and thresholds are in `src/config.py`. You can tune them without touching scorer code.

Key parameters:
- `WEIGHTS` — how much each scoring dimension contributes to the final score
- `MUST_HAVE_SKILLS` / `NICE_TO_HAVE_SKILLS` — derived from JD analysis
- `CONSULTING_COMPANIES` — companies flagged by the JD as poor fit
- `IDEAL_EXP_MIN` / `IDEAL_EXP_MAX` — experience range from JD (5-9 years)

## What Could Be Improved Next

- **Learn-to-rank**: Train weights from recruiter feedback data instead of hand-tuning
- **Cross-encoder reranking**: Add a second-stage cross-encoder on the top-100 shortlist for better precision
- **Semantic skill matching**: Use skill embeddings instead of string matching for skill comparison
- **Fine-tuned embeddings**: Train the embedding model on JD-resume pairs from the recruiting domain
- **Salary compatibility**: Score candidates based on expected salary vs role budget
- **Anomaly detection**: Replace heuristic honeypot checks with a learned anomaly detector

## Tech Stack

- **Embeddings**: sentence-transformers (`all-MiniLM-L6-v2`)
- **Vector Search**: FAISS (IndexFlatIP)
- **Data**: pandas, numpy
- **UI**: Streamlit
- **Presentation**: python-pptx
- **Language**: Python 3.10+

## Compute Requirements

- **Pre-computation**: ~10-20 min on CPU, ~3GB RAM
- **Ranking**: <5 min on CPU, <16GB RAM, no network
- **No GPU required**
