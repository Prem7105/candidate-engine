"""
Honeypot detection logic.

The dataset contains ~80 candidates with subtly impossible profiles.
Things like 8 years at a company founded 3 years ago, or "expert"
proficiency in 10 skills with 0 months of usage.

We need to catch these because ranking them in the top 100 is
a disqualification risk (>10% honeypot rate = DQ'd).
"""

import logging
from datetime import date
from src.cleaner import parse_date

logger = logging.getLogger(__name__)


def detect_honeypot(candidate: dict) -> tuple[bool, list[str]]:
    """
    Check if a candidate profile has impossible or highly suspicious data.

    Returns:
        (is_honeypot: bool, reasons: list[str])
    """
    flags = []

    # --- Check 1: Experience years vs career history duration ---
    profile = candidate.get("profile", {})
    stated_years = profile.get("years_of_experience", 0)
    career = candidate.get("career_history", [])

    if career:
        total_career_months = sum(
            job.get("duration_months", 0) for job in career
        )
        career_years = total_career_months / 12.0

        # If stated experience is way more than career history adds up to
        if stated_years > 0 and career_years > 0:
            ratio = stated_years / career_years
            if ratio > 2.0:
                flags.append(
                    f"Stated {stated_years:.1f} yrs but career history "
                    f"only adds to {career_years:.1f} yrs"
                )

    # --- Check 2: Expert proficiency with zero duration ---
    skills = candidate.get("skills", [])
    expert_zero_count = 0
    for skill in skills:
        prof = skill.get("proficiency", "")
        duration = skill.get("duration_months", 0)
        if prof in ("expert", "advanced") and duration == 0:
            expert_zero_count += 1

    if expert_zero_count >= 3:
        flags.append(
            f"{expert_zero_count} skills listed as expert/advanced "
            f"with 0 months duration"
        )

    # --- Check 3: Too many expert skills relative to experience ---
    expert_count = sum(
        1 for s in skills if s.get("proficiency") == "expert"
    )
    if expert_count >= 8 and stated_years < 5:
        flags.append(
            f"{expert_count} expert-level skills with only "
            f"{stated_years:.1f} years experience"
        )
        
    # --- Check 3b: Explicit rubric trap checks ---
    # 0 years experience + Expert in LLMs
    if stated_years == 0:
        has_expert_llm = any(
            s.get("proficiency") == "expert" and "llm" in s.get("name", "").lower()
            for s in skills
        )
        if has_expert_llm:
            flags.append("0 years experience + 'Expert in LLMs'")

    # Marketing manager with 15 AI skills
    current_title = (profile.get("current_title", "") or "").lower()
    if "marketing" in current_title and len(skills) >= 15:
        ai_skill_count = sum(
            1 for s in skills if s.get("name", "").lower() in ["python", "pytorch", "llms", "machine learning", "ai"]
        )
        if ai_skill_count >= 5: # If they have a ton of AI skills but are in marketing
            flags.append("Marketing manager with excessive AI skills (Keyword stuffing)")

    # --- Check 4: Career dates that don't make sense ---
    for job in career:
        start = parse_date(job.get("start_date"))
        end = parse_date(job.get("end_date"))
        duration = job.get("duration_months", 0)

        if start and end:
            actual_months = (end.year - start.year) * 12 + (end.month - start.month)
            # Duration claimed vs date range mismatch
            if duration > 0 and abs(actual_months - duration) > 12:
                flags.append(
                    f"Job at {job.get('company', '?')}: dates span "
                    f"{actual_months} months but duration says {duration}"
                )

        # Future start dates
        if start and start > date.today():
            flags.append(f"Job at {job.get('company', '?')} starts in the future")

    # --- Check 5: Impossible endorsement patterns ---
    # E.g., beginner skills with very high endorsements, or 0-duration with high endorsements
    for skill in skills:
        prof = skill.get("proficiency", "")
        endorsements = skill.get("endorsements", 0)
        duration = skill.get("duration_months", 0)
        
        if prof == "beginner" and endorsements > 40:
            flags.append(
                f"Skill '{skill.get('name')}': beginner with "
                f"{endorsements} endorsements"
            )
            
        if duration == 0 and endorsements >= 50:
            flags.append(
                f"Skill '{skill.get('name')}': 0 months duration but "
                f"{endorsements} endorsements"
            )

    # --- Check 6: Profile completeness vs actual content mismatch ---
    signals = candidate.get("redrob_signals", {})
    completeness = signals.get("profile_completeness_score", 50)

    # Very high completeness but minimal actual content
    if completeness > 90:
        has_summary = bool(profile.get("summary", "").strip())
        has_career = len(career) > 0
        has_skills = len(skills) > 0
        if not has_summary or not has_career or not has_skills:
            flags.append(
                f"Profile completeness {completeness}% but missing "
                f"basic sections"
            )

    # --- Decision ---
    # 2+ flags = very likely honeypot
    # 1 flag = suspicious but could be data quality issue
    is_honeypot = len(flags) >= 2

    if is_honeypot:
        cid = candidate.get("candidate_id", "?")
        logger.debug(f"Honeypot detected: {cid} — {flags}")

    return is_honeypot, flags
