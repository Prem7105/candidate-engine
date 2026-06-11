"""Tests for the scoring components."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def test_semantic_scorer():
    scorer = SemanticScorer()

    # High similarity should give high score
    assert scorer.score(0.7) > 0.8
    # Low similarity should give low score
    assert scorer.score(0.1) < 0.1
    # Mid-range
    assert 0.3 < scorer.score(0.4) < 0.7
    print("  ✓ SemanticScorer")


def test_experience_scorer():
    scorer = ExperienceFitScorer()

    # Perfect range
    for years in [5, 6, 7, 8, 9]:
        cand = {"profile": {"years_of_experience": years}}
        assert scorer.score(cand) == 1.0, f"Expected 1.0 for {years} years"

    # Too junior
    cand = {"profile": {"years_of_experience": 1.0}}
    assert scorer.score(cand) < 0.3

    # Slightly outside range (should still be decent)
    cand = {"profile": {"years_of_experience": 4.0}}
    assert scorer.score(cand) > 0.5

    # Way too senior
    cand = {"profile": {"years_of_experience": 20.0}}
    assert scorer.score(cand) < 0.5

    print("  ✓ ExperienceFitScorer")


def test_location_scorer():
    scorer = LocationScorer()

    # Pune should be perfect
    cand = {
        "profile": {"location": "Pune, Maharashtra", "country": "India"},
        "redrob_signals": {"willing_to_relocate": True, "preferred_work_mode": "hybrid"},
    }
    assert scorer.score(cand) == 1.0

    # Bangalore with relocation
    cand["profile"]["location"] = "Bangalore"
    assert scorer.score(cand) > 0.7

    # International, no relocation
    cand["profile"]["location"] = "San Francisco"
    cand["profile"]["country"] = "USA"
    cand["redrob_signals"]["willing_to_relocate"] = False
    assert scorer.score(cand) < 0.3

    print("  ✓ LocationScorer")


def test_honeypot_detection():
    # Clean candidate
    clean = {
        "candidate_id": "CAND_0000001",
        "profile": {"years_of_experience": 6.0},
        "career_history": [
            {"company": "Google", "title": "ML Engineer",
             "start_date": "2020-01-01", "end_date": None,
             "duration_months": 60, "is_current": True,
             "description": "Built ML systems"}
        ],
        "skills": [
            {"name": "Python", "proficiency": "advanced",
             "endorsements": 20, "duration_months": 48}
        ],
        "redrob_signals": {"profile_completeness_score": 85},
    }
    is_hp, reasons = detect_honeypot(clean)
    assert not is_hp, f"Clean candidate flagged as honeypot: {reasons}"

    # Honeypot: expert skills with 0 duration
    honeypot = {
        "candidate_id": "CAND_9999999",
        "profile": {"years_of_experience": 3.0},
        "career_history": [
            {"company": "Fake Co", "title": "Engineer",
             "start_date": "2023-01-01", "end_date": None,
             "duration_months": 12, "is_current": True,
             "description": "Work"}
        ],
        "skills": [
            {"name": "ML", "proficiency": "expert", "endorsements": 50, "duration_months": 0},
            {"name": "AI", "proficiency": "expert", "endorsements": 50, "duration_months": 0},
            {"name": "DL", "proficiency": "advanced", "endorsements": 50, "duration_months": 0},
            {"name": "NLP", "proficiency": "expert", "endorsements": 50, "duration_months": 0},
        ],
        "redrob_signals": {"profile_completeness_score": 95},
    }
    is_hp, reasons = detect_honeypot(honeypot)
    assert is_hp, f"Honeypot not detected. Flags: {reasons}"

    print("  ✓ Honeypot Detection")


def test_skill_relevance_scorer():
    scorer = SkillRelevanceScorer()

    # Strong candidate with relevant skills
    strong = {
        "skills": [
            {"name": "Python", "proficiency": "advanced", "endorsements": 30, "duration_months": 60},
            {"name": "FAISS", "proficiency": "intermediate", "endorsements": 10, "duration_months": 24},
            {"name": "embeddings", "proficiency": "advanced", "endorsements": 20, "duration_months": 36},
            {"name": "ranking", "proficiency": "intermediate", "endorsements": 5, "duration_months": 18},
        ],
        "career_history": [
            {"description": "Built embedding-based retrieval systems and ranking pipelines in Python"}
        ],
        "redrob_signals": {"skill_assessment_scores": {"Python": 85}},
    }
    score, details = scorer.score(strong)
    assert score > 0.5, f"Strong candidate scored too low: {score}"

    # Weak candidate: keyword stuffer
    weak = {
        "skills": [
            {"name": "Python", "proficiency": "beginner", "endorsements": 0, "duration_months": 0},
            {"name": "FAISS", "proficiency": "beginner", "endorsements": 0, "duration_months": 0},
            {"name": "embeddings", "proficiency": "beginner", "endorsements": 0, "duration_months": 0},
        ],
        "career_history": [
            {"description": "Managed marketing campaigns and social media"}
        ],
        "redrob_signals": {"skill_assessment_scores": {}},
    }
    weak_score, _ = scorer.score(weak)
    assert weak_score < score, f"Keyword stuffer scored higher than real candidate"

    print("  ✓ SkillRelevanceScorer")


def test_career_trajectory_scorer():
    scorer = CareerTrajectoryScorer()

    # Strong: AI Engineer at product company
    strong = {
        "profile": {"current_title": "ML Engineer", "current_company": "Flipkart"},
        "career_history": [
            {"company": "Flipkart", "title": "ML Engineer", "duration_months": 36,
             "description": "Built production recommendation systems serving millions of users"},
            {"company": "Google", "title": "Software Engineer", "duration_months": 24,
             "description": "Worked on search ranking infrastructure at scale"},
        ],
    }
    strong_score, _ = scorer.score(strong)

    # Weak: Marketing Manager at consulting firm
    weak = {
        "profile": {"current_title": "Marketing Manager", "current_company": "TCS"},
        "career_history": [
            {"company": "TCS", "title": "Marketing Manager", "duration_months": 24,
             "description": "Managed marketing campaigns"},
            {"company": "Infosys", "title": "Business Analyst", "duration_months": 18,
             "description": "Business analysis and process improvement"},
        ],
    }
    weak_score, _ = scorer.score(weak)

    assert strong_score > weak_score, (
        f"Career scorer broken: ML@Flipkart ({strong_score:.2f}) "
        f"should beat Marketing@TCS ({weak_score:.2f})"
    )
    print("  ✓ CareerTrajectoryScorer")


if __name__ == "__main__":
    print("Running scorer tests...")
    test_semantic_scorer()
    test_experience_scorer()
    test_location_scorer()
    test_honeypot_detection()
    test_skill_relevance_scorer()
    test_career_trajectory_scorer()
    print("\nAll tests passed ✓")
