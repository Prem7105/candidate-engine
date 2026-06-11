"""
Text cleaning and normalization utilities.

Handles the messy, inconsistent text you get in real candidate profiles:
mixed casing, unicode junk, inconsistent skill names, etc.
"""

import re
import unicodedata
from datetime import datetime, date


def normalize_text(text: str | None) -> str:
    """
    Basic text normalization: lowercase, strip whitespace,
    collapse multiple spaces, remove control characters.
    """
    if not text:
        return ""

    # Normalize unicode (handle curly quotes, em dashes, etc.)
    text = unicodedata.normalize("NFKD", text)

    # Lowercase
    text = text.lower().strip()

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_skill_name(skill: str) -> str:
    """
    Standardize a skill name for comparison.

    Maps common variations to a canonical form, e.g.:
    "Scikit-Learn" -> "scikit-learn"
    "TensorFlow 2.x" -> "tensorflow"
    """
    s = normalize_text(skill)

    # Strip version numbers
    s = re.sub(r"\s*\d+(\.\d+)*\s*$", "", s)
    s = re.sub(r"\s*v\d+.*$", "", s)

    # Common aliases
    aliases = {
        "sci-kit learn": "scikit-learn",
        "sklearn": "scikit-learn",
        "tf": "tensorflow",
        "pytorch": "pytorch",
        "torch": "pytorch",
        "k8s": "kubernetes",
        "postgres": "postgresql",
        "mongo": "mongodb",
        "es": "elasticsearch",
        "elastic search": "elasticsearch",
        "sentence transformers": "sentence-transformers",
        "hugging face": "huggingface",
        "hf": "huggingface",
        "llms": "llm",
        "large language models": "llm",
        "natural language processing": "nlp",
        "machine learning": "machine learning",
        "ml": "machine learning",
        "deep learning": "deep learning",
        "dl": "deep learning",
        "artificial intelligence": "ai",
        "information retrieval": "information retrieval",
        "ir": "information retrieval",
    }

    return aliases.get(s, s)


def extract_skills_from_candidate(candidate: dict) -> list[dict]:
    """
    Pull the skills list from a candidate profile, normalizing names.
    Returns list of dicts with name, proficiency, endorsements, duration_months.
    """
    raw_skills = candidate.get("skills", [])
    cleaned = []
    for skill in raw_skills:
        name = normalize_skill_name(skill.get("name", ""))
        if not name:
            continue
        cleaned.append({
            "name": name,
            "proficiency": skill.get("proficiency", "beginner"),
            "endorsements": skill.get("endorsements", 0),
            "duration_months": skill.get("duration_months", 0),
        })
    return cleaned


def build_candidate_text(candidate: dict) -> str:
    """
    Build a single text blob from a candidate's profile for embedding.

    Concatenates headline, summary, career descriptions, and skill names
    into a single string that captures what this person actually does.
    """
    parts = []

    profile = candidate.get("profile", {})
    if profile.get("headline"):
        parts.append(profile["headline"])
    if profile.get("summary"):
        parts.append(profile["summary"])
    if profile.get("current_title"):
        parts.append(f"Current role: {profile['current_title']}")
    if profile.get("current_industry"):
        parts.append(f"Industry: {profile['current_industry']}")

    # Career history — the descriptions contain the real signal
    for job in candidate.get("career_history", []):
        desc = job.get("description", "")
        title = job.get("title", "")
        if desc:
            parts.append(f"{title}: {desc}")

    # Skills as a comma-separated list
    skills = candidate.get("skills", [])
    if skills:
        skill_names = [s.get("name", "") for s in skills if s.get("name")]
        parts.append("Skills: " + ", ".join(skill_names))

    # Education fields
    for edu in candidate.get("education", []):
        field = edu.get("field_of_study", "")
        degree = edu.get("degree", "")
        if field:
            parts.append(f"Education: {degree} in {field}")

    return " ".join(parts)


def parse_date(date_str: str | None) -> date | None:
    """Parse a date string (YYYY-MM-DD format) into a date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def days_since(date_str: str | None, reference: date | None = None) -> int | None:
    """Calculate days between a date string and today (or a reference date)."""
    d = parse_date(date_str)
    if d is None:
        return None
    ref = reference or date.today()
    return (ref - d).days
