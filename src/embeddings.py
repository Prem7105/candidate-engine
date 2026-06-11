"""
Embedding generation and FAISS index management.

Uses sentence-transformers (all-MiniLM-L6-v2) to encode candidate
profiles into dense vectors. Builds a FAISS index for fast retrieval
of the top-K most semantically similar candidates to a query (the JD).
"""

import logging
import pickle
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    Wraps sentence-transformers for encoding and FAISS for retrieval.

    The model is loaded lazily on first use to keep imports fast
    when you only need other parts of the codebase.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        return self._model

    def encode(self, texts: list[str], batch_size: int = 256,
               show_progress: bool = True) -> np.ndarray:
        """
        Encode a list of texts into normalized embeddings.

        Returns an (N, D) numpy array where D is the embedding dimension
        (384 for MiniLM). Vectors are L2-normalized so dot product = cosine sim.
        """
        logger.info(f"Encoding {len(texts)} texts (batch_size={batch_size})")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,  # so we can use inner product = cosine
            convert_to_numpy=True,
        )

        logger.info(f"Embeddings shape: {embeddings.shape}")
        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text. Returns a (D,) vector."""
        return self.encode([text], show_progress=False)[0]


class CrossEncoderEngine:
    """
    Wraps the sentence-transformers CrossEncoder for second-stage reranking.
    
    Cross-encoders take pairs of (query, document) and output a relevance score.
    They are much more accurate than bi-encoders but too slow to run on all 100K candidates.
    We run this only on the top-K retrieved by the FAISS index.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self._model = CrossEncoder(self.model_name)
            logger.info("Cross-encoder model loaded successfully")
        return self._model

    def rerank(self, query: str, documents: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Score pairs of (query, document).
        Returns an array of scores (not normalized, raw logits).
        """
        logger.info(f"Cross-encoding {len(documents)} pairs (batch_size={batch_size})")
        
        # Create pairs
        pairs = [[query, doc] for doc in documents]
        
        # Score pairs
        scores = self.model.predict(pairs, batch_size=batch_size, show_progress_bar=False)
        return scores


def build_faiss_index(embeddings: np.ndarray):
    """
    Build a FAISS index from normalized embeddings.

    Uses IndexFlatIP (inner product) since our embeddings are L2-normalized,
    which means inner product = cosine similarity. FlatIP is exact search,
    which is fine for 100K vectors — takes ~50ms per query.
    """
    import faiss

    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(embeddings.astype(np.float32))

    logger.info(f"Built FAISS index with {index.ntotal} vectors (dim={d})")
    return index


def search_index(index, query_embedding: np.ndarray, top_k: int = 500):
    """
    Search the FAISS index for the top-K most similar candidates.

    Returns:
        scores: (top_k,) array of similarity scores
        indices: (top_k,) array of candidate indices
    """
    import faiss

    query = query_embedding.reshape(1, -1).astype(np.float32)
    scores, indices = index.search(query, top_k)
    return scores[0], indices[0]


def save_artifacts(embeddings: np.ndarray, index, candidate_ids: list[str],
                   output_dir: str):
    """Save precomputed embeddings and FAISS index to disk."""
    import faiss

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save embeddings
    np.save(output_path / "embeddings.npy", embeddings)

    # Save FAISS index
    faiss.write_index(index, str(output_path / "faiss.index"))

    # Save candidate ID mapping (index position -> candidate_id)
    with open(output_path / "candidate_ids.pkl", "wb") as f:
        pickle.dump(candidate_ids, f)

    logger.info(f"Saved artifacts to {output_dir}")


def load_artifacts(artifact_dir: str):
    """Load precomputed embeddings and FAISS index from disk."""
    import faiss

    artifact_path = Path(artifact_dir)

    if not (artifact_path / "faiss.index").exists():
        raise FileNotFoundError(
            f"No precomputed artifacts found in {artifact_dir}. "
            f"Run precompute.py first."
        )

    embeddings = np.load(artifact_path / "embeddings.npy")
    index = faiss.read_index(str(artifact_path / "faiss.index"))

    with open(artifact_path / "candidate_ids.pkl", "rb") as f:
        candidate_ids = pickle.load(f)

    logger.info(
        f"Loaded {len(candidate_ids)} embeddings and FAISS index "
        f"from {artifact_dir}"
    )

    return embeddings, index, candidate_ids
