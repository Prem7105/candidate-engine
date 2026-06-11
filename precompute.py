"""
Pre-computation step: generate embeddings and FAISS index for all candidates.

This runs BEFORE the ranking step and can take longer than 5 minutes.
The results are saved to disk so the actual ranking step (rank.py)
can load them quickly and stay within the 5-minute budget.

Usage:
    python precompute.py --candidates ./candidates.jsonl --output ./models
"""

import argparse
import logging
import time
from pathlib import Path

from src.loader import load_candidates, stream_candidates
from src.cleaner import build_candidate_text
from src.embeddings import EmbeddingEngine, build_faiss_index, save_artifacts
from src.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Pre-compute embeddings and FAISS index for candidate pool"
    )
    parser.add_argument(
        "--candidates", required=True,
        help="Path to candidates.jsonl or candidates.jsonl.gz"
    )
    parser.add_argument(
        "--output", default="./models",
        help="Directory to save embeddings and FAISS index"
    )
    parser.add_argument(
        "--batch-size", type=int, default=EMBEDDING_BATCH_SIZE,
        help="Batch size for embedding generation"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit number of candidates (for testing)"
    )
    args = parser.parse_args()

    start_time = time.time()

    # Load candidates
    logger.info(f"Loading candidates from {args.candidates}...")
    candidates = load_candidates(args.candidates, limit=args.limit)
    logger.info(f"Loaded {len(candidates)} candidates")

    # Build text representations
    logger.info("Building text representations for embedding...")
    texts = []
    candidate_ids = []
    for c in candidates:
        text = build_candidate_text(c)
        texts.append(text)
        candidate_ids.append(c["candidate_id"])

    # Generate embeddings
    engine = EmbeddingEngine(EMBEDDING_MODEL)
    embeddings = engine.encode(texts, batch_size=args.batch_size)

    # Build FAISS index
    logger.info("Building FAISS index...")
    index = build_faiss_index(embeddings)

    # Save everything
    save_artifacts(embeddings, index, candidate_ids, args.output)

    elapsed = time.time() - start_time
    logger.info(
        f"Pre-computation complete in {elapsed:.1f}s. "
        f"Artifacts saved to {args.output}/"
    )
    logger.info(
        f"  Embeddings: {embeddings.shape[0]} vectors × {embeddings.shape[1]} dims"
    )
    logger.info(f"  Index size: {index.ntotal} vectors")


if __name__ == "__main__":
    main()
