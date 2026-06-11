"""
Data loading utilities for the candidate ranking pipeline.

Handles JSONL and gzipped JSONL files, with streaming support
for large files (100K candidates ~ 487MB).
"""

import gzip
import json
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def load_candidates(path: str, limit: int | None = None) -> list[dict]:
    """
    Load all candidates from a JSONL file into memory.

    For the full 100K dataset this uses ~2-3GB of RAM, which is
    fine for our 16GB budget. If memory were tighter we'd use
    the streaming version instead.
    """
    candidates = []
    for i, candidate in enumerate(stream_candidates(path)):
        if limit and i >= limit:
            break
        candidates.append(candidate)

    logger.info(f"Loaded {len(candidates)} candidates from {path}")
    return candidates


def stream_candidates(path: str) -> Iterator[dict]:
    """
    Stream candidates one at a time from a JSONL or gzipped JSONL file.
    Useful when you don't want to hold everything in memory at once.
    """
    filepath = Path(path)

    if not filepath.exists():
        raise FileNotFoundError(f"Candidate file not found: {path}")

    opener = gzip.open if filepath.suffix == ".gz" else open
    mode = "rt" if filepath.suffix == ".gz" else "r"

    with opener(filepath, mode, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed JSON at line {line_num}: {e}")
                continue


def load_jd(path: str) -> dict:
    """Load the structured job description from a JSON file."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"JD file not found: {path}")

    with open(filepath, "r", encoding="utf-8") as f:
        jd = json.load(f)

    logger.info(f"Loaded JD: {jd.get('title', 'Unknown')}")
    return jd


def load_sample_candidates(path: str) -> list[dict]:
    """Load the sample_candidates.json file (regular JSON array)."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Sample file not found: {path}")

    with open(filepath, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    logger.info(f"Loaded {len(candidates)} sample candidates from {path}")
    return candidates
