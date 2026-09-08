"""
Master Orchestrator
Runs all pipeline phases in order and builds the analytics-ready dataset.
"""

import sys
import json
import warnings
import pandas as pd
from pathlib import Path
from tqdm import tqdm

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import PROCESSED_DATA_PATH, DATA_DIR, MODELS_DIR, MIN_PATTERN_SUPPORT
from backend.services.data_pipeline import run_pipeline, save_processed
from backend.services.nlp_extractor import extract_all
from backend.services.sif_classifier import analyze_report
from backend.services.similarity_engine import SimilarityEngine, PatternDetector
from backend.services.analytics_engine import get_kpi_summary


def run_full_pipeline(force_rebuild: bool = False) -> pd.DataFrame:
    """
    Execute all phases of the SIF intelligence platform pipeline.
    Returns the fully enriched DataFrame.
    """
    enriched_path = DATA_DIR / "processed" / "enriched_dataset.csv"

    if enriched_path.exists() and not force_rebuild:
        print("[Orchestrator] Loading cached enriched dataset...")
        df = pd.read_csv(enriched_path, dtype=str)
        df["sif_risk_score"] = pd.to_numeric(df["sif_risk_score"], errors="coerce").fillna(0)
        return df

    # ── Phase 1: Data ingestion and normalization ──────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 1: Data Ingestion & Normalization")
    print("=" * 60)
    df = run_pipeline()

    # ── Phase 2–7: NLP extraction + SIF analysis ──────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2–7: NLP Extraction + SIF Analysis")
    print("=" * 60)

    records = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Analyzing reports"):
        text = str(row.get("clean_text", ""))
        extracted = extract_all(text)
        analysis = analyze_report(row, extracted)

        # Merge back
        updated = row.to_dict()
        updated.update({
            # Extraction
            "hazards": json.dumps(analysis.get("hazards", [])),
            "unsafe_acts": json.dumps(analysis.get("unsafe_acts", [])),
            "unsafe_conditions": json.dumps(analysis.get("unsafe_conditions", [])),
            "barriers_present": json.dumps(analysis.get("barriers_present", [])),
            "barriers_missing": json.dumps(analysis.get("barriers_missing", [])),
            "barrier_failures": json.dumps(analysis.get("barrier_failures", [])),
            "life_saving_rules": json.dumps(analysis.get("life_saving_rules", [])),
            "contributing_factors": json.dumps(analysis.get("contributing_factors", [])),
            "explanation": json.dumps(analysis.get("explanation", [])),
            "evidence_spans": json.dumps(analysis.get("evidence_spans", [])),
            # Classification
            "sif_label": analysis.get("sif_label", "Non-SIF"),
            "sif_probability": analysis.get("sif_probability", 0.0),
            "sif_risk_score": analysis.get("sif_risk_score", 0),
            "potential_consequence": analysis.get("potential_consequence", "Low"),
            "fatal_potential": analysis.get("fatal_potential", False),
            "label_source": analysis.get("label_source", "heuristic"),
            # Severity
            "actual_severity": row.get("actual_severity", "Unknown"),
        })
        records.append(updated)

    df = pd.DataFrame(records)
    print(f"\n[Orchestrator] Analysis complete: {len(df)} reports processed")

    # ── Phase 8: Embeddings + similarity ──────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 8: Embeddings + Similar Incident Index")
    print("=" * 60)

    engine = SimilarityEngine()
    engine.load_model()
    engine.build_index(df)

    # Add similar incident IDs to each report
    similar_ids = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Building similarity index"):
        sims = engine.find_similar(
            str(row.get("clean_text", "")),
            exclude_id=row["report_id"],
            top_k=3,
        )
        similar_ids.append(json.dumps([s["report_id"] for s in sims]))
    df["similar_incident_ids"] = similar_ids
    print("[Orchestrator] Similarity index built")

    # ── Phase 9: Pattern detection ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 9: Recurring Precursor Pattern Detection")
    print("=" * 60)

    detector = PatternDetector()
    patterns_df = detector.detect_patterns(df, min_support=MIN_PATTERN_SUPPORT)

    if len(patterns_df):
        patterns_path = DATA_DIR / "processed" / "patterns.csv"
        patterns_path.parent.mkdir(parents=True, exist_ok=True)
        patterns_df.to_csv(patterns_path, index=False)
        print(f"[Orchestrator] {len(patterns_df)} patterns detected → {patterns_path}")

        # Tag reports with pattern IDs
        pattern_map = {}
        for _, p_row in patterns_df.iterrows():
            for rid in (p_row.get("report_ids") or []):
                if rid not in pattern_map:
                    pattern_map[rid] = []
                pattern_map[rid].append(p_row["pattern_id"])

        df["pattern_ids"] = df["report_id"].map(
            lambda rid: json.dumps(pattern_map.get(rid, []))
        )
    else:
        print("[Orchestrator] No patterns detected with current minimum support")
        df["pattern_ids"] = "[]"

    # ── Save enriched dataset ──────────────────────────────────────────────
    enriched_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(enriched_path, index=False)
    print(f"\n[Orchestrator] Enriched dataset saved → {enriched_path}")

    # ── Print KPI summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE — KPI SUMMARY")
    print("=" * 60)
    kpi = get_kpi_summary(df)
    for k, v in kpi.items():
        print(f"  {k}: {v}")

    # Store the engine for API use (module-level singleton)
    _store_engine(engine)

    return df


# Singleton engine storage for API
_engine_singleton: SimilarityEngine = None


def _store_engine(engine: SimilarityEngine):
    global _engine_singleton
    _engine_singleton = engine


def get_engine() -> SimilarityEngine:
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = SimilarityEngine()
        _engine_singleton.load_model()
        enriched_path = DATA_DIR / "processed" / "enriched_dataset.csv"
        if enriched_path.exists():
            df = pd.read_csv(enriched_path, dtype=str)
            _engine_singleton.build_index(df)
    return _engine_singleton


if __name__ == "__main__":
    df = run_full_pipeline(force_rebuild=True)
    print(f"\nFinal dataset shape: {df.shape}")
    print(df[["report_id", "sif_label", "sif_risk_score", "potential_consequence"]].head(10).to_string())
