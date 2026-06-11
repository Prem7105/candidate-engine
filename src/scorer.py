"""
Scoring components for the candidate ranking system.

Each scorer takes a candidate dict and the JD, and returns a score
between 0 and 1. The final ranking combines these with configurable weights.

The design goal: a Marketing Manager who listed 9 AI keywords should
score low, while an ML Engineer at a product company with 6 years of
embeddings experience should score high — even if their keyword count
is lower.
"""

import math
import logging
from datetime import date
from src.cleaner import normalize_skill_name, extract_skills_from_candidate, days_since
from src import config

logger = logging.getLogger(__name__)


class SemanticScorer:
    """
    Score based on cosine similarity between candidate profile embedding
    and the JD embedding. This comes from the FAISS retrieval step.

    The raw cosine similarity from sentence-transformers typically ranges
    from about 0.1 to 0.8 for this kind of data. We rescale it to [0, 1]
    so it plays nicely with the other scorers.
    """

    def score(self, similarity: float) -> float:
        # Rescale from typical [0.1, 0.7] range to [0, 1]
        # Anything below 0.15 is basically noise
        scaled = max(0.0, (similarity - 0.15) / 0.55)
        return min(1.0, scaled)


class SkillRelevanceScorer:
    """
    Scores how well a candidate's skills match the JD requirements.

    This is NOT keyword counting. The JD explicitly warns against that.
    Instead we:
    1. Weight must-have skills much more than nice-to-haves
    2. Use skill proficiency + duration as a "trust" multiplier
    3. Check Redrob skill assessment scores when available
    4. Penalize keyword-stuffing patterns (many skills, low duration/proficiency)
    """

    def score(self, candidate: dict) -> tuple[float, dict]:
        skills = extract_skills_from_candidate(candidate)
        skill_names = {s["name"] for s in skills}

        # Check must-have skills
        must_have_matches = skill_names & config.MUST_HAVE_SKILLS
        nice_to_have_matches = skill_names & config.NICE_TO_HAVE_SKILLS

        # Must-have score (0 to 1) — hitting all of them is hard,
        # so we give full credit at around 4-5 matches
        must_have_score = min(1.0, len(must_have_matches) / 5.0)

        # Nice-to-have score — bonus credit, softer curve
        nice_score = min(1.0, len(nice_to_have_matches) / 6.0)

        # Trust multiplier: penalize keyword stuffing
        # If someone has lots of skills all at beginner/0-duration, that's suspicious
        trust = self._compute_trust(skills)

        # Check skill assessment scores from Redrob platform
        assessment_bonus = self._assessment_bonus(candidate)

        # Career text check: do their job descriptions mention these skills?
        career_depth = self._career_skill_depth(candidate)

        # Combine: must-haves weighted heavily, nice-to-haves lighter
        raw = (
            0.45 * must_have_score
            + 0.15 * nice_score
            + 0.15 * trust
            + 0.10 * assessment_bonus
            + 0.15 * career_depth
        )

        details = {
            "must_have_matches": sorted(must_have_matches),
            "nice_to_have_matches": sorted(nice_to_have_matches),
            "trust": round(trust, 3),
            "assessment_bonus": round(assessment_bonus, 3),
        }

        return min(1.0, raw), details

    def _compute_trust(self, skills: list[dict]) -> float:
        """
        Trust score — high when skills have real depth indicators.
        Low when lots of skills are listed as expert but with no duration.
        """
        if not skills:
            return 0.0

        depth_scores = []
        for s in skills:
            prof_weight = {
                "expert": 1.0, "advanced": 0.75,
                "intermediate": 0.5, "beginner": 0.2
            }.get(s["proficiency"], 0.2)

            # Duration gives credibility — 12+ months of usage is real
            dur = s["duration_months"]
            dur_weight = min(1.0, dur / 24.0) if dur > 0 else 0.1

            # Endorsements add a small signal
            end_weight = min(1.0, s["endorsements"] / 20.0)

            depth_scores.append(
                0.4 * prof_weight + 0.4 * dur_weight + 0.2 * end_weight
            )

        return sum(depth_scores) / len(depth_scores)

    def _assessment_bonus(self, candidate: dict) -> float:
        """
        Bonus from Redrob platform skill assessments.
        These are actual tests, so they're more trustworthy than self-reported.
        """
        signals = candidate.get("redrob_signals", {})
        scores = signals.get("skill_assessment_scores", {})

        if not scores:
            return 0.0

        # Check if any assessed skills overlap with what we care about
        relevant_scores = []
        for skill_name, score_val in scores.items():
            normalized = normalize_skill_name(skill_name)
            if normalized in config.MUST_HAVE_SKILLS or normalized in config.NICE_TO_HAVE_SKILLS:
                relevant_scores.append(score_val / 100.0)

        if not relevant_scores:
            # They took assessments but not in relevant areas
            avg_all = sum(scores.values()) / len(scores) / 100.0
            return avg_all * 0.3  # Small credit for taking any assessments

        return sum(relevant_scores) / len(relevant_scores)

    def _career_skill_depth(self, candidate: dict) -> float:
        """
        Check if career descriptions actually mention relevant technical work.
        A Marketing Manager can list "embeddings" as a skill, but if none
        of their job descriptions mention anything technical, that's a red flag.
        """
        career = candidate.get("career_history", [])
        if not career:
            return 0.0

        # Build text from all job descriptions
        career_text = " ".join(
            job.get("description", "").lower()
            for job in career
        )

        if not career_text.strip():
            return 0.0

        # Count how many relevant terms appear in actual work descriptions
        relevant_terms = [
            "embedding", "retrieval", "ranking", "vector", "search",
            "machine learning", "ml", "model", "pipeline", "nlp",
            "neural", "deep learning", "training", "inference",
            "python", "data science", "recommendation", "pytorch",
            "tensorflow", "transformer", "llm", "fine-tun",
            "evaluation", "ndcg", "precision", "recall",
            "spark", "airflow", "data engineer", "etl",
        ]

        hits = sum(1 for term in relevant_terms if term in career_text)
        return min(1.0, hits / 8.0)


class ExperienceFitScorer:
    """
    Score based on how well the candidate's experience aligns with the JD.

    The JD says 5-9 years, but also says the range is flexible.
    We use a smooth curve centered on the ideal range, not a hard cutoff.
    """

    def score(self, candidate: dict) -> float:
        profile = candidate.get("profile", {})
        years = profile.get("years_of_experience", 0)

        if years <= 0:
            return 0.0

        # Perfect range: 5-9 years
        if config.IDEAL_EXP_MIN <= years <= config.IDEAL_EXP_MAX:
            return 1.0

        # Gaussian decay outside the ideal range
        if years < config.IDEAL_EXP_MIN:
            distance = config.IDEAL_EXP_MIN - years
            sigma = 2.5  # How quickly score drops
        else:
            distance = years - config.IDEAL_EXP_MAX
            sigma = 4.0  # More lenient for over-experience

        score = math.exp(-(distance ** 2) / (2 * sigma ** 2))

        # Below 2 years is almost certainly too junior
        if years < 2.0:
            score *= 0.3

        return max(0.0, min(1.0, score))


class CareerTrajectoryScorer:
    """
    Evaluate the candidate's career path for fit with this specific role.

    The JD is very clear about what it doesn't want:
    - Consulting-only careers
    - Pure research without production
    - Non-technical roles pretending to be AI-relevant
    - Title-chasers with 1.5-year stints

    And what it does want:
    - Product company experience
    - AI/ML/Engineering roles
    - Actually shipping production systems
    """

    def score(self, candidate: dict) -> tuple[float, dict]:
        profile = candidate.get("profile", {})
        career = candidate.get("career_history", [])

        current_title = (profile.get("current_title", "") or "").lower()
        current_company = (profile.get("current_company", "") or "").lower()

        scores = {}

        # 1. Title relevance — is this person actually in a technical role?
        scores["title_fit"] = self._title_fit(current_title, career)

        # 2. Company type — product vs consulting
        scores["company_fit"] = self._company_fit(career, current_company)

        # 3. Career stability — not a job hopper
        scores["stability"] = self._stability(career)

        # 4. Career descriptions — do they describe production/engineering work?
        scores["production_exp"] = self._production_signals(career)

        # Combine with weights
        combined = (
            0.35 * scores["title_fit"]
            + 0.25 * scores["company_fit"]
            + 0.15 * scores["stability"]
            + 0.25 * scores["production_exp"]
        )

        return min(1.0, combined), scores

    def _title_fit(self, current_title: str, career: list[dict]) -> float:
        """How relevant is their title history to this AI engineering role?"""
        all_titles = [current_title]
        all_titles.extend(
            (job.get("title", "") or "").lower() for job in career
        )

        strong_matches = sum(
            1 for t in all_titles
            if any(st in t for st in config.STRONG_FIT_TITLES)
        )
        weak_matches = sum(
            1 for t in all_titles
            if any(wt in t for wt in config.WEAK_FIT_TITLES)
        )

        # Current title matters most
        current_is_strong = any(st in current_title for st in config.STRONG_FIT_TITLES)
        current_is_weak = any(wt in current_title for wt in config.WEAK_FIT_TITLES)

        if current_is_strong:
            base = 0.8
        elif current_is_weak:
            # Stricter penalty for non-technical current titles (Marketing Manager trap)
            base = 0.05
        else:
            base = 0.4

        # Historical titles add or subtract
        history_bonus = min(0.2, strong_matches * 0.1) if not current_is_weak else 0.0
        history_penalty = min(0.2, weak_matches * 0.05)

        return max(0.0, min(1.0, base + history_bonus - history_penalty))

    def _company_fit(self, career: list[dict], current_company: str) -> float:
        """
        Product companies > consulting firms.
        The JD explicitly says consulting-only is a disqualifier.
        """
        companies = [current_company]
        companies.extend(
            (job.get("company", "") or "").lower() for job in career
        )

        consulting_count = sum(
            1 for c in companies
            if any(cc in c for cc in config.CONSULTING_COMPANIES)
        )
        product_count = sum(
            1 for c in companies
            if any(pc in c for pc in config.PRODUCT_COMPANY_SIGNALS)
        )

        total = len(companies)
        if total == 0:
            return 0.3

        # All consulting = bad, mixed = ok, product-heavy = good
        if consulting_count == total and product_count == 0:
            return 0.1  # Consulting-only career
        elif product_count > 0:
            return min(1.0, 0.5 + product_count * 0.15)
        else:
            # Unknown companies — neutral
            return 0.4

    def _stability(self, career: list[dict]) -> float:
        """
        Check for job-hopper patterns. The JD explicitly doesn't want
        people optimizing for titles by switching every 1.5 years.
        """
        if not career:
            return 0.3

        durations = [job.get("duration_months", 0) for job in career]
        if not durations:
            return 0.3

        avg_duration = sum(durations) / len(durations)
        short_stints = sum(1 for d in durations if d < 18)

        if avg_duration >= 30:
            base = 0.9
        elif avg_duration >= 24:
            base = 0.7
        elif avg_duration >= 18:
            base = 0.5
        else:
            base = 0.3

        # Penalty for too many short stints
        penalty = min(0.3, short_stints * 0.1)

        return max(0.0, base - penalty)

    def _production_signals(self, career: list[dict]) -> float:
        """
        Check career descriptions for production engineering signals.
        Research-only or non-technical descriptions score lower.
        """
        if not career:
            return 0.0

        career_text = " ".join(
            (job.get("description", "") or "").lower()
            for job in career
        )

        production_terms = [
            "production", "deploy", "shipped", "scale", "users",
            "pipeline", "infrastructure", "system", "api", "service",
            "monitoring", "latency", "throughput", "a/b test",
            "real-time", "batch", "index", "search", "retrieval",
        ]

        research_only_terms = [
            "research paper", "publication", "thesis", "academic",
            "laboratory", "theoretical",
        ]

        prod_hits = sum(1 for t in production_terms if t in career_text)
        research_hits = sum(1 for t in research_only_terms if t in career_text)

        prod_score = min(1.0, prod_hits / 5.0)

        # Penalty if it's all research, no production
        if research_hits > 2 and prod_hits < 2:
            prod_score *= 0.3

        return prod_score


class BehavioralScorer:
    """
    Score based on Redrob platform behavioral signals.

    The JD says: "A perfect-on-paper candidate who hasn't logged in
    for 6 months and has a 5% recruiter response rate is, for hiring
    purposes, not actually available."

    These signals tell us whether the candidate is actually reachable
    and interested, which matters a lot for practical recruiting.
    """

    def score(self, candidate: dict) -> tuple[float, dict]:
        signals = candidate.get("redrob_signals", {})
        scores = {}

        # 1. Recruiter response rate — huge signal
        response_rate = signals.get("recruiter_response_rate", 0)
        scores["response_rate"] = self._score_response_rate(response_rate)

        # 2. Recency — when did they last log in?
        last_active = signals.get("last_active_date")
        scores["recency"] = self._score_recency(last_active)

        # 3. Open to work
        open_to_work = signals.get("open_to_work_flag", False)
        scores["availability"] = 0.8 if open_to_work else 0.3

        # 4. Notice period
        notice = signals.get("notice_period_days", 90)
        scores["notice_period"] = self._score_notice(notice)

        # 5. Interview completion rate
        interview_rate = signals.get("interview_completion_rate", 0.5)
        scores["interview_reliability"] = min(1.0, interview_rate)

        # 6. Profile completeness
        completeness = signals.get("profile_completeness_score", 50)
        scores["profile_quality"] = completeness / 100.0

        # 7. GitHub activity (tech signal)
        github = signals.get("github_activity_score", -1)
        scores["github"] = self._score_github(github)

        # 8. Verification signals
        verified = (
            (1 if signals.get("verified_email", False) else 0)
            + (1 if signals.get("verified_phone", False) else 0)
            + (1 if signals.get("linkedin_connected", False) else 0)
        )
        scores["verification"] = verified / 3.0

        # Combine with weights — response rate and recency are most important
        combined = (
            0.25 * scores["response_rate"]
            + 0.20 * scores["recency"]
            + 0.10 * scores["availability"]
            + 0.15 * scores["notice_period"]
            + 0.10 * scores["interview_reliability"]
            + 0.05 * scores["profile_quality"]
            + 0.10 * scores["github"]
            + 0.05 * scores["verification"]
        )

        return min(1.0, combined), scores

    def _score_response_rate(self, rate: float) -> float:
        if rate >= 0.7:
            return 1.0
        elif rate >= 0.4:
            return 0.7
        elif rate >= 0.2:
            return 0.4
        elif rate >= 0.1:
            return 0.2
        else:
            return 0.05  # Basically unreachable

    def _score_recency(self, last_active: str | None) -> float:
        if not last_active:
            return 0.2

        days = days_since(last_active)
        if days is None:
            return 0.2

        if days <= 30:
            return 1.0
        elif days <= 60:
            return 0.8
        elif days <= 90:
            return 0.6
        elif days <= 180:
            return 0.3
        else:
            return 0.1  # 6+ months inactive

    def _score_notice(self, notice_days: int) -> float:
        if notice_days <= 30:
            return 1.0
        elif notice_days <= 60:
            return 0.7
        elif notice_days <= 90:
            return 0.4
        else:
            return 0.2

    def _score_github(self, score: float) -> float:
        if score < 0:
            return 0.3  # No GitHub linked — neutral, not penalized
        return min(1.0, score / 60.0)


class LocationScorer:
    """
    Score based on location fit.

    Pune/Noida preferred, Tier-1 Indian cities acceptable,
    international candidates considered case-by-case (no visa sponsorship).
    """

    def score(self, candidate: dict) -> float:
        profile = candidate.get("profile", {})
        location = (profile.get("location", "") or "").lower()
        country = (profile.get("country", "") or "").lower()

        signals = candidate.get("redrob_signals", {})
        relocate = signals.get("willing_to_relocate", False)
        work_mode = signals.get("preferred_work_mode", "")

        # Preferred locations
        if any(loc in location for loc in config.PREFERRED_LOCATIONS):
            return 1.0

        # Other Tier-1 Indian cities
        if any(loc in location for loc in config.TIER1_INDIA_CITIES):
            if relocate:
                return 0.85
            return 0.7

        # India but not Tier-1
        if country == "india":
            if relocate:
                return 0.65
            return 0.5

        # International — case by case, JD says no visa sponsorship
        if relocate:
            return 0.3
        return 0.15


class EducationScorer:
    """
    Light scoring on education — the JD doesn't emphasize this much,
    but a CS/ML degree from a good institution is a mild positive.
    """

    RELEVANT_FIELDS = {
        "computer science", "machine learning", "artificial intelligence",
        "data science", "information technology", "software engineering",
        "statistics", "mathematics", "electrical engineering",
        "electronics", "information systems",
    }

    TIER_SCORES = {
        "tier_1": 1.0,
        "tier_2": 0.7,
        "tier_3": 0.4,
        "tier_4": 0.2,
        "unknown": 0.3,
    }

    def score(self, candidate: dict) -> float:
        education = candidate.get("education", [])
        if not education:
            return 0.2  # No education info — don't penalize too hard

        best_score = 0.0
        for edu in education:
            field = (edu.get("field_of_study", "") or "").lower()
            tier = edu.get("tier", "unknown")
            degree = (edu.get("degree", "") or "").lower()

            # Field relevance
            field_relevant = any(f in field for f in self.RELEVANT_FIELDS)
            field_score = 0.6 if field_relevant else 0.2

            # Institution tier
            tier_score = self.TIER_SCORES.get(tier, 0.3)

            # Higher degrees get a small bump
            degree_bump = 0.0
            if any(d in degree for d in ["m.tech", "m.sc", "m.s.", "ms", "mtech"]):
                degree_bump = 0.1
            elif any(d in degree for d in ["ph.d", "phd"]):
                degree_bump = 0.15

            edu_score = 0.5 * field_score + 0.35 * tier_score + 0.15 * (0.5 + degree_bump)
            best_score = max(best_score, edu_score)

        return min(1.0, best_score)
