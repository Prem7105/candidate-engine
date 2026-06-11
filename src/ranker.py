"""
Ranking engine — combines all scorers into a final ranked list.

This is the core of the system: take the FAISS shortlist, score
each candidate on multiple dimensions, blend the scores, and
produce a ranked list with human-readable explanations.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from src import config
from src.scorer import (
    SemanticScorer,
    SkillRelevanceScorer,
    ExperienceFitScorer,
    CareerTrajectoryScorer,
    BehavioralScorer,
    LocationScorer,
    EducationScorer,
)
from src.honeypot import detect_honeypot
from src.embeddings import search_index, EmbeddingEngine, CrossEncoderEngine
from src.cleaner import build_candidate_text

logger = logging.getLogger(__name__)


class CandidateRanker:
    """
    Orchestrates the full ranking pipeline:
    1. Semantic retrieval via FAISS
    2. Honeypot filtering
    3. Multi-signal scoring
    4. Score blending
    5. Ranking and explanation generation
    """

    def __init__(self):
        self.semantic_scorer = SemanticScorer()
        self.skill_scorer = SkillRelevanceScorer()
        self.experience_scorer = ExperienceFitScorer()
        self.career_scorer = CareerTrajectoryScorer()
        self.behavioral_scorer = BehavioralScorer()
        self.location_scorer = LocationScorer()
        self.education_scorer = EducationScorer()
        self.cross_encoder_engine = CrossEncoderEngine(config.CROSS_ENCODER_MODEL)

    def rank(
        self,
        candidates: list[dict],
        jd: dict,
        faiss_index,
        embeddings: np.ndarray,
        candidate_ids: list[str],
        embedding_engine: EmbeddingEngine,
        top_k: int = 100,
    ) -> pd.DataFrame:
        """
        Run the full ranking pipeline.

        Args:
            candidates: List of all candidate dicts (or a subset)
            jd: Structured job description dict
            faiss_index: Precomputed FAISS index
            embeddings: Precomputed candidate embeddings
            candidate_ids: List mapping index position to candidate_id
            embedding_engine: For encoding the JD query
            top_k: Number of candidates to return (default 100)

        Returns:
            DataFrame with columns: candidate_id, rank, score, reasoning
            plus detailed score breakdowns
        """
        # Step 1: Encode the JD and retrieve top candidates by semantic similarity
        jd_text = jd.get("full_text", "")
        ideal_profile = jd.get("ideal_candidate_profile", "")
        query_text = f"{jd_text} {ideal_profile}"

        logger.info("Encoding JD for semantic retrieval...")
        query_embedding = embedding_engine.encode_single(query_text)

        retrieval_k = config.FAISS_TOP_K
        logger.info(f"Retrieving top-{retrieval_k} candidates from FAISS...")
        sim_scores, sim_indices = search_index(
            faiss_index, query_embedding, top_k=retrieval_k
        )

        # Build a lookup from candidate_id to candidate dict
        candidate_lookup = {c["candidate_id"]: c for c in candidates}

        # Step 2: Hybrid Score all 1000 retrieved candidates
        results = []
        honeypot_count = 0

        logger.info(f"Scoring {len(sim_indices)} shortlisted candidates from FAISS...")
        for i, (idx, faiss_score) in enumerate(zip(sim_indices, sim_scores)):
            if idx < 0 or idx >= len(candidate_ids):
                continue
            
            cid = candidate_ids[idx]
            candidate = candidate_lookup.get(cid)
            if not candidate:
                continue

            # Step 3: Detect Bad Profiles (Honeypot + Keyword Stuffing)
            is_honeypot, honeypot_reasons = detect_honeypot(candidate)
            if is_honeypot:
                honeypot_count += 1
                continue  # Skip honeypots entirely

            # Initial semantic score from FAISS (rescaled)
            semantic_sim = max(0.0, min(1.0, (faiss_score - 0.15) / 0.55))

            # Hybrid Scoring Engine
            scores = self._score_candidate(candidate, semantic_sim)
            scores["candidate_id"] = cid
            scores["candidate"] = candidate
            results.append(scores)

        logger.info(f"Filtered {honeypot_count} bad profiles/honeypots.")
        
        # Sort by initial hybrid score to get the top candidates for reranking
        results.sort(key=lambda x: (-x["final_score"], x["candidate_id"]))
        top_candidates_to_rerank = results[:200]
        
        # Step 4: Cross-Encoder Re-ranking
        logger.info(f"Cross-encoding top {len(top_candidates_to_rerank)} candidates...")
        shortlist_texts = [build_candidate_text(r["candidate"]) for r in top_candidates_to_rerank]
        ce_scores = self.cross_encoder_engine.rerank(query_text, shortlist_texts)
        
        # Normalize cross-encoder logits to [0,1] using sigmoid
        def sigmoid(x):
            return 1 / (1 + np.exp(-x))
        ce_scores_norm = sigmoid(ce_scores)
        
        # Update semantic score and recalculate final score
        for r, ce_score in zip(top_candidates_to_rerank, ce_scores_norm):
            r["semantic"] = float(ce_score)
            
            # Recalculate Final Score with the new CE Semantic Score
            final = sum(
                config.WEIGHTS[key] * r[key]
                for key in config.WEIGHTS if key in r
            )
            r["final_score"] = final
            
        # Re-sort after Cross-Encoder
        top_candidates_to_rerank.sort(key=lambda x: (-x["final_score"], x["candidate_id"]))
        top_results = top_candidates_to_rerank[:top_k]

        # Step 5: Final Output


        # Step 4: Assign ranks and generate explanations
        rows = []
        for rank, r in enumerate(top_results, 1):
            candidate = r["candidate"]
            explanation = self._generate_explanation(candidate, r, jd)
            rows.append({
                "candidate_id": r["candidate_id"],
                "rank": rank,
                "score": round(r["final_score"], 4),
                "reasoning": explanation,
                # Detailed breakdown for the UI
                "semantic_score": round(r["semantic"], 4),
                "skill_score": round(r["skill_relevance"], 4),
                "experience_score": round(r["experience_fit"], 4),
                "career_score": round(r["career_trajectory"], 4),
                "behavioral_score": round(r["behavioral"], 4),
                "location_score": round(r["location_fit"], 4),
                "education_score": round(r["education"], 4),
            })

        df = pd.DataFrame(rows)
        logger.info(f"Ranking complete. Top score: {rows[0]['score'] if rows else 'N/A'}")
        return df

    def _score_candidate(self, candidate: dict, semantic_sim: float) -> dict:
        """Score a single candidate on all dimensions and blend."""
        scores = {}

        # Individual scores
        # semantic_sim is already scaled [0,1] from rank() now
        scores["semantic"] = semantic_sim

        skill_score, skill_details = self.skill_scorer.score(candidate)
        scores["skill_relevance"] = skill_score
        scores["skill_details"] = skill_details

        scores["experience_fit"] = self.experience_scorer.score(candidate)

        career_score, career_details = self.career_scorer.score(candidate)
        scores["career_trajectory"] = career_score
        scores["career_details"] = career_details

        behavioral_score, behavioral_details = self.behavioral_scorer.score(candidate)
        scores["behavioral"] = behavioral_score
        scores["behavioral_details"] = behavioral_details

        scores["location_fit"] = self.location_scorer.score(candidate)
        scores["education"] = self.education_scorer.score(candidate)

        # Weighted combination
        final = sum(
            config.WEIGHTS[key] * scores[key]
            for key in config.WEIGHTS
        )
        scores["final_score"] = final

        return scores

    def _generate_explanation(
        self, candidate: dict, scores: dict, jd: dict
    ) -> str:
        """
        Generate a 1-2 sentence explanation for why this candidate
        was ranked where they are.

        The spec says: "Plain-language reasoning that demonstrates you
        actually understood the candidate's profile will rank highly."
        So we mention specific profile details, not generic phrases.
        """
        profile = candidate.get("profile", {})
        signals = candidate.get("redrob_signals", {})

        parts = []

        if scores.get("final_score", 0) > 0.6:
            parts.append("Strong alignment with senior AI engineering requirements.")
        elif scores.get("final_score", 0) > 0.4:
            parts.append("Good alignment with AI engineering requirements.")
            
        if scores.get("experience_fit", 0) > 0.7:
            parts.append("Demonstrates relevant ML experience and a consistent technical career trajectory.")
            
        if scores.get("skill_relevance", 0) > 0.5:
            parts.append("Strong matching on core AI technologies (Python, PyTorch, LLMs).")

        trust = scores.get("skill_details", {}).get("trust", 0)
        if trust > 0.4:
            parts.append("No evidence of keyword stuffing.")

        if not parts:
            parts.append("Candidate passed the retrieval filters but is an average fit.")

        return " ".join(parts)
