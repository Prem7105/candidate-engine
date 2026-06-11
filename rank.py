"""
Main ranking script — produces the submission CSV.

This is the entry point that must run within the 5-minute, 16GB, CPU-only
constraint. It loads precomputed artifacts (embeddings + FAISS index),
scores and ranks candidates, and writes the submission file.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

If precomputed artifacts don't exist yet, it will run precomputation first
(which may exceed the 5-minute window — that's allowed per the spec).
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Rank top 100 candidates for the Redrob AI Senior AI Engineer role"
    )
    parser.add_argument(
        "--candidates", required=True,
        help="Path to candidates.jsonl or candidates.jsonl.gz"
    )
    parser.add_argument(
        "--out", default="./outputs/submission.csv",
        help="Output path for the submission CSV"
    )
    parser.add_argument(
        "--jd", default="./data/jd.json",
        help="Path to the structured JD JSON file"
    )
    parser.add_argument(
        "--models-dir", default="./models",
        help="Directory containing precomputed embeddings and FAISS index"
    )
    parser.add_argument(
        "--top-k", type=int, default=100,
        help="Number of candidates to include in the ranking"
    )
    parser.add_argument(
        "--skip-precompute", action="store_true",
        help="Skip precomputation even if artifacts are missing (will fail)"
    )
    args = parser.parse_args()

    start_time = time.time()

    # Check if precomputed artifacts exist
    models_dir = Path(args.models_dir)
    if not (models_dir / "faiss.index").exists():
        if args.skip_precompute:
            logger.error(
                f"No precomputed artifacts found in {args.models_dir}. "
                f"Run precompute.py first."
            )
            sys.exit(1)

        logger.info("No precomputed artifacts found. Running precomputation...")
        import subprocess
        result = subprocess.run(
            [sys.executable, "precompute.py",
             "--candidates", args.candidates,
             "--output", args.models_dir],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        if result.returncode != 0:
            logger.error("Precomputation failed.")
            sys.exit(1)

    # Now do the actual ranking (this part must be under 5 minutes)
    rank_start = time.time()
    logger.info("=" * 60)
    logger.info("Starting ranking step...")
    logger.info("=" * 60)

    # Import after precomputation to avoid loading models we might not need
    from src.loader import load_candidates, load_jd
    from src.embeddings import load_artifacts, EmbeddingEngine
    from src.ranker import CandidateRanker
    from src.exporter import export_submission_csv, export_detailed_csv
    from src.config import EMBEDDING_MODEL

    # Load JD
    jd = load_jd(args.jd)
    logger.info(f"JD: {jd['title']} at {jd['company']}")

    # Load precomputed artifacts
    embeddings, faiss_index, candidate_ids = load_artifacts(args.models_dir)

    # Load all candidates (we need the full profiles for scoring)
    candidates = load_candidates(args.candidates)

    # Initialize the embedding engine (for encoding the JD query)
    engine = EmbeddingEngine(EMBEDDING_MODEL)

    # Run the ranking
    ranker = CandidateRanker()
    ranked_df = ranker.rank(
        candidates=candidates,
        jd=jd,
        faiss_index=faiss_index,
        embeddings=embeddings,
        candidate_ids=candidate_ids,
        embedding_engine=engine,
        top_k=args.top_k,
    )

    # Export submission CSV
    export_submission_csv(ranked_df, args.out)

    # Also save a detailed version with score breakdowns
    detailed_path = str(Path(args.out).parent / "detailed_results.csv")
    export_detailed_csv(ranked_df, detailed_path)

    rank_elapsed = time.time() - rank_start
    total_elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info(f"Ranking complete in {rank_elapsed:.1f}s")
    logger.info(f"Total elapsed: {total_elapsed:.1f}s")
    logger.info(f"Submission saved to: {args.out}")
    logger.info(f"Detailed results: {detailed_path}")
    logger.info("=" * 60)

    # Print top-10 summary
    print("\nTop 10 candidates:")
    print("-" * 90)
    for _, row in ranked_df.head(10).iterrows():
        print(
            f"  #{row['rank']:>3}  {row['candidate_id']}  "
            f"score={row['score']:.4f}  {row['reasoning'][:80]}..."
        )
    print("-" * 90)


if __name__ == "__main__":
    main()
