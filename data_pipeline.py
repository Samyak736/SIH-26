"""
Data Ingestion and Preprocessing Pipeline
Phase 1: Dataset normalization, cleaning, quality checks
"""

import re
import sys
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import (
    RAW_DATA_PATH, PROCESSED_DATA_PATH,
    SEVERITY_WEIGHTS, ACTUAL_SEVERITY_LEVELS, DATA_DIR
)


# ─── Text Cleaning ────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Normalize free-text safety report."""
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.strip()
    # Remove HTML artifacts
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Basic encoding fix for common mojibake
    text = text.replace("â€", "-").replace("â€™", "'").replace("â€˜", "'")
    return text.strip()


def normalize_site(site: str) -> str:
    """Standardize site names."""
    if not isinstance(site, str):
        return "Unknown"
    return site.strip().replace("  ", " ").title()


def normalize_severity(val: str) -> str:
    """Map various severity strings to canonical values."""
    if not isinstance(val, str):
        return "Unknown"
    val_lower = val.lower().strip()
    mapping = {
        "fatal": "Fatality",
        "fatality": "Fatality",
        "death": "Fatality",
        "severe": "Severe Injury",
        "hospitalized": "Hospitalized",
        "hospitalized": "Hospitalized",
        "hospitalised": "Hospitalized",
        "medical treatment": "Medical Treatment",
        "medical": "Medical Treatment",
        "moderate": "Medical Treatment",
        "near miss": "No Injury",
        "near-miss": "No Injury",
        "no injury": "No Injury",
        "no fatality": "No Injury",
        "first aid": "First Aid",
        "minor": "First Aid",
        "lost time": "Lost Time",
        "major incident": "Hospitalized",
    }
    for k, v in mapping.items():
        if k in val_lower:
            return v
    return "Unknown"


def parse_date(val) -> str:
    """Parse date to ISO string."""
    if pd.isna(val) or val == "":
        return None
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return None


# ─── Deduplication ────────────────────────────────────────────────────────────

def make_content_hash(row: pd.Series) -> str:
    """Create a stable content hash for deduplication."""
    content = f"{row.get('raw_text', '')}|{row.get('report_date', '')}|{row.get('site', '')}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


# ─── Quality Checks ───────────────────────────────────────────────────────────

def assess_quality(row: pd.Series) -> dict:
    """Return quality flags for a report."""
    flags = []
    score = 100

    text = row.get("clean_text", "")
    if not text:
        flags.append("EMPTY_TEXT")
        score -= 50
    elif len(text.split()) < 10:
        flags.append("VERY_SHORT")
        score -= 20

    if not row.get("report_date"):
        flags.append("MISSING_DATE")
        score -= 10

    if not row.get("site") or row.get("site") == "Unknown":
        flags.append("MISSING_SITE")
        score -= 5

    if not row.get("activity") or str(row.get("activity")).lower() == "nan":
        flags.append("MISSING_ACTIVITY")
        score -= 5

    return {"quality_flags": "|".join(flags) if flags else "OK", "quality_score": max(0, score)}


# ─── Main Pipeline ────────────────────────────────────────────────────────────

def load_and_normalize(path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    """Load CSV and produce a normalized DataFrame."""
    df = pd.read_csv(path, dtype=str)
    df = df.fillna("")

    # ── Core fields ──
    df["report_id"] = df["report_id"].str.strip()
    df["source"] = df["source"].str.strip().str.upper()
    df["site"] = df["site"].apply(normalize_site)
    df["location"] = df["location"].str.strip().str.title()
    df["activity"] = df["activity"].str.strip().str.title()
    df["report_type"] = df["report_type"].str.strip()

    # ── Text ──
    df["raw_text"] = df["raw_text"].apply(lambda x: x.strip() if isinstance(x, str) else "")
    df["clean_text"] = df["raw_text"].apply(clean_text)

    # ── Dates ──
    df["report_date"] = df["report_date"].apply(parse_date)

    # ── Severity ──
    df["actual_severity_raw"] = df["actual_severity"].copy()
    df["actual_severity"] = df["actual_severity"].apply(normalize_severity)
    df["actual_outcome"] = df["actual_outcome"].str.strip()

    # ── Deduplication ──
    df["content_hash"] = df.apply(make_content_hash, axis=1)
    before = len(df)
    df = df.drop_duplicates(subset=["content_hash"], keep="first").reset_index(drop=True)
    print(f"[Pipeline] Deduplicated: {before} → {len(df)} reports")

    # ── Quality ──
    quality_results = df.apply(assess_quality, axis=1)
    df["quality_flags"] = quality_results.apply(lambda x: x["quality_flags"])
    df["quality_score"] = quality_results.apply(lambda x: x["quality_score"])

    # ── Severity weight (numeric) ──
    df["severity_weight"] = df["actual_severity"].map(
        lambda s: SEVERITY_WEIGHTS.get(s, 0.2)
    )

    # ── Placeholder fields for downstream pipeline ──
    for field in [
        "hazards", "unsafe_acts", "unsafe_conditions",
        "barriers_present", "barriers_missing", "barrier_failures",
        "potential_consequence", "potential_severity", "fatal_potential",
        "sif_label", "sif_probability", "sif_risk_score",
        "life_saving_rules", "root_causes", "contributing_factors",
        "explanation", "similar_incident_ids", "pattern_ids",
        "review_status", "human_verified", "model_version",
    ]:
        if field not in df.columns:
            df[field] = ""

    df["model_version"] = "v1.0-prototype"
    df["review_status"] = "Pending"
    df["human_verified"] = False

    print(f"[Pipeline] Loaded {len(df)} reports from {path.name}")
    return df


def save_processed(df: pd.DataFrame, path: Path = PROCESSED_DATA_PATH) -> None:
    """Save processed dataset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"[Pipeline] Saved processed dataset → {path}")


def run_pipeline() -> pd.DataFrame:
    df = load_and_normalize()
    save_processed(df)
    return df


if __name__ == "__main__":
    df = run_pipeline()
    print(df[["report_id", "source", "site", "actual_severity", "quality_flags"]].to_string())
