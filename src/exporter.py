"""
Export ranked results to the required submission CSV format.

Format spec:
- Header: candidate_id,rank,score,reasoning
- Exactly 100 data rows
- Scores non-increasing with rank
- Candidate IDs unique, ranks 1-100 unique
"""

import csv
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def export_submission_csv(
    ranked_df: pd.DataFrame,
    output_path: str,
    validate: bool = True,
) -> str:
    """
    Export the ranked results to the submission CSV format.

    Takes the full DataFrame from the ranker (which may have extra columns
    for the UI) and writes only the required columns.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Select only the required columns
    submission = ranked_df[["candidate_id", "rank", "score", "reasoning"]].copy()

    # Make sure we have exactly 100 rows
    if len(submission) < 100:
        logger.warning(
            f"Only {len(submission)} candidates ranked. "
            f"Submission requires exactly 100."
        )
    elif len(submission) > 100:
        submission = submission.head(100)

    # Ensure scores are non-increasing
    submission = submission.sort_values("rank")

    # Write CSV
    submission.to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
    logger.info(f"Submission CSV saved to {output}")

    if validate:
        errors = validate_submission(submission)
        if errors:
            logger.warning(f"Validation found {len(errors)} issues:")
            for e in errors:
                logger.warning(f"  - {e}")
        else:
            logger.info("Submission passed validation checks.")

    return str(output)


def export_detailed_csv(ranked_df: pd.DataFrame, output_path: str) -> str:
    """
    Export a detailed version with all score breakdowns.
    This one is for our own analysis, not for submission.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ranked_df.to_csv(output, index=False)
    logger.info(f"Detailed results saved to {output}")
    return str(output)


def validate_submission(df: pd.DataFrame) -> list[str]:
    """
    Run the same validation checks as the official validate_submission.py
    so we catch problems before uploading.
    """
    errors = []

    # Check row count
    if len(df) != 100:
        errors.append(f"Expected 100 rows, got {len(df)}")

    # Check required columns
    required = ["candidate_id", "rank", "score", "reasoning"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"Missing columns: {missing}")
        return errors

    # Check unique candidate_ids
    if df["candidate_id"].duplicated().any():
        dupes = df[df["candidate_id"].duplicated()]["candidate_id"].tolist()
        errors.append(f"Duplicate candidate_ids: {dupes}")

    # Check unique ranks 1-100
    ranks = set(df["rank"].tolist())
    expected_ranks = set(range(1, 101))
    if ranks != expected_ranks:
        missing_ranks = expected_ranks - ranks
        if missing_ranks:
            errors.append(f"Missing ranks: {sorted(missing_ranks)}")

    # Check scores are non-increasing
    scores = df.sort_values("rank")["score"].tolist()
    for i in range(len(scores) - 1):
        if scores[i] < scores[i + 1]:
            errors.append(
                f"Scores not non-increasing at rank {i+1}: "
                f"{scores[i]} < {scores[i+1]}"
            )
            break

    # Check candidate_id format
    import re
    pattern = re.compile(r"^CAND_\d{7}$")
    for cid in df["candidate_id"]:
        if not pattern.match(str(cid)):
            errors.append(f"Invalid candidate_id format: {cid}")

    return errors
