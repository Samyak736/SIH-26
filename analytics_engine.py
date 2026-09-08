"""
Analytics Engine
Phase 10–11: Leading indicators, site ranking, heatmap, trend analysis
"""

import sys
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import SIF_THRESHOLDS

warnings.filterwarnings("ignore")


def _parse_list(val) -> List[str]:
    """Parse a list field that may be stored as string or list."""
    if isinstance(val, list):
        return [str(v).strip() for v in val if v]
    if isinstance(val, str):
        if val.startswith("["):
            try:
                parsed = json.loads(val.replace("'", '"'))
                return [str(v).strip() for v in parsed if v]
            except Exception:
                pass
        return [v.strip() for v in val.split(",") if v.strip()]
    return []


def _sif_tier(score) -> str:
    s = int(score or 0)
    if s >= SIF_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    if s >= SIF_THRESHOLDS["HIGH"]:
        return "HIGH"
    if s >= SIF_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


# ─── KPI Summary ─────────────────────────────────────────────────────────────

def get_kpi_summary(df: pd.DataFrame) -> Dict:
    total = len(df)
    sif_potential = df[df["sif_label"].isin(["High-Confidence SIF", "Potential SIF"])].shape[0]
    high_sif = df[df["sif_risk_score"].apply(lambda x: int(x or 0)) >= SIF_THRESHOLDS["HIGH"]].shape[0]
    high_potential_no_injury = df[
        (df["sif_label"].isin(["High-Confidence SIF", "Potential SIF"]))
        & (df["actual_severity"].isin(["No Injury", "Near Miss", "First Aid"]))
    ].shape[0]

    # Top failed barrier
    all_failures = []
    for val in df["barrier_failures"]:
        all_failures.extend(_parse_list(val))
    top_barrier = pd.Series(all_failures).value_counts().index[0] if all_failures else "N/A"

    # Top LSR
    all_lsr = []
    for val in df["life_saving_rules"]:
        all_lsr.extend(_parse_list(val))
    top_lsr = pd.Series(all_lsr).value_counts().index[0] if all_lsr else "N/A"

    # Highest risk site
    site_scores = df.groupby("site")["sif_risk_score"].apply(
        lambda x: pd.to_numeric(x, errors="coerce").mean()
    )
    top_site = site_scores.idxmax() if len(site_scores) else "N/A"

    return {
        "total_reports": total,
        "sif_potential_reports": int(sif_potential),
        "high_sif_risk_reports": int(high_sif),
        "high_potential_no_injury": int(high_potential_no_injury),
        "top_failed_barrier": str(top_barrier),
        "top_life_saving_rule": str(top_lsr),
        "highest_risk_site": str(top_site),
        "sif_rate_pct": round(sif_potential / total * 100, 1) if total else 0,
    }


# ─── Trend Analysis ───────────────────────────────────────────────────────────

def get_sif_trend(df: pd.DataFrame) -> List[Dict]:
    """Monthly SIF precursor trend."""
    df2 = df.copy()
    df2["report_date"] = pd.to_datetime(df2["report_date"], errors="coerce")
    df2 = df2.dropna(subset=["report_date"])
    df2["month"] = df2["report_date"].dt.to_period("M").astype(str)

    grouped = df2.groupby("month").agg(
        total=("report_id", "count"),
        sif_potential=("sif_label", lambda x: x.isin(["High-Confidence SIF", "Potential SIF"]).sum()),
        avg_score=("sif_risk_score", lambda x: pd.to_numeric(x, errors="coerce").mean()),
    ).reset_index()

    grouped["avg_score"] = grouped["avg_score"].fillna(0).round(1)
    return grouped.to_dict("records")


# ─── Severity vs Potential ────────────────────────────────────────────────────

def get_severity_vs_potential(df: pd.DataFrame) -> List[Dict]:
    """
    Cross-tabulation of actual_severity vs potential_consequence.
    Shows leading indicator value (No Injury + High Potential).
    """
    ct = pd.crosstab(
        df["actual_severity"].fillna("Unknown"),
        df["potential_consequence"].fillna("Unknown"),
    )
    result = []
    for actual_sev, row in ct.iterrows():
        for pot_cons, count in row.items():
            if count > 0:
                result.append({
                    "actual_severity": actual_sev,
                    "potential_consequence": pot_cons,
                    "count": int(count),
                })
    return result


# ─── Site Ranking ─────────────────────────────────────────────────────────────

def get_site_ranking(df: pd.DataFrame) -> List[Dict]:
    """Rank sites by SIF precursor density and average risk score."""
    df2 = df.copy()
    df2["sif_risk_score_num"] = pd.to_numeric(df2["sif_risk_score"], errors="coerce").fillna(0)
    df2["is_sif"] = df2["sif_label"].isin(["High-Confidence SIF", "Potential SIF"])

    grouped = df2.groupby("site").agg(
        total_reports=("report_id", "count"),
        sif_reports=("is_sif", "sum"),
        avg_risk_score=("sif_risk_score_num", "mean"),
        fatality_count=("actual_severity", lambda x: (x == "Fatality").sum()),
        hospitalized_count=("actual_severity", lambda x: (x == "Hospitalized").sum()),
    ).reset_index()

    grouped["sif_density_pct"] = (
        grouped["sif_reports"] / grouped["total_reports"] * 100
    ).round(1)
    grouped["avg_risk_score"] = grouped["avg_risk_score"].round(1)
    grouped["risk_tier"] = grouped["avg_risk_score"].apply(_sif_tier)

    return grouped.sort_values("avg_risk_score", ascending=False).to_dict("records")


# ─── Activity Ranking ─────────────────────────────────────────────────────────

def get_activity_ranking(df: pd.DataFrame) -> List[Dict]:
    df2 = df.copy()
    df2["sif_risk_score_num"] = pd.to_numeric(df2["sif_risk_score"], errors="coerce").fillna(0)
    df2["is_sif"] = df2["sif_label"].isin(["High-Confidence SIF", "Potential SIF"])

    grouped = df2.groupby("activity").agg(
        total_reports=("report_id", "count"),
        sif_reports=("is_sif", "sum"),
        avg_risk_score=("sif_risk_score_num", "mean"),
    ).reset_index()

    grouped["sif_density_pct"] = (
        grouped["sif_reports"] / grouped["total_reports"] * 100
    ).round(1)
    grouped["avg_risk_score"] = grouped["avg_risk_score"].round(1)
    return grouped.sort_values("avg_risk_score", ascending=False).head(15).to_dict("records")


# ─── Hazard Distribution ──────────────────────────────────────────────────────

def get_hazard_distribution(df: pd.DataFrame) -> List[Dict]:
    all_hazards = []
    for _, row in df.iterrows():
        h_list = _parse_list(row["hazards"])
        score = float(row.get("sif_risk_score", 0) or 0)
        is_sif = row.get("sif_label", "") in ("High-Confidence SIF", "Potential SIF")
        for h in h_list:
            all_hazards.append({
                "hazard": h,
                "sif_risk_score": score,
                "is_sif": is_sif,
            })

    if not all_hazards:
        return []

    hazard_df = pd.DataFrame(all_hazards)
    grouped = hazard_df.groupby("hazard").agg(
        count=("hazard", "count"),
        avg_score=("sif_risk_score", "mean"),
        sif_count=("is_sif", "sum"),
    ).reset_index()
    grouped["avg_score"] = grouped["avg_score"].round(1)
    return grouped.sort_values("count", ascending=False).head(12).to_dict("records")


# ─── Barrier Failure Distribution ─────────────────────────────────────────────

def get_barrier_failure_distribution(df: pd.DataFrame) -> List[Dict]:
    all_failures = []
    for val in df["barrier_failures"]:
        all_failures.extend(_parse_list(val))
    if not all_failures:
        return []
    counts = pd.Series(all_failures).value_counts().reset_index()
    counts.columns = ["barrier", "count"]
    return counts.head(10).to_dict("records")


# ─── Life-Saving Rule Distribution ───────────────────────────────────────────

def get_lsr_distribution(df: pd.DataFrame) -> List[Dict]:
    all_lsr = []
    for val in df["life_saving_rules"]:
        all_lsr.extend(_parse_list(val))
    if not all_lsr:
        return []
    counts = pd.Series(all_lsr).value_counts().reset_index()
    counts.columns = ["rule", "count"]
    return counts.head(10).to_dict("records")


# ─── Risk Heatmap ─────────────────────────────────────────────────────────────

def get_risk_heatmap(
    df: pd.DataFrame,
    row_dim: str = "site",
    col_dim: str = "life_saving_rules",
) -> Dict:
    """
    Build a heatmap of avg SIF risk score across two dimensions.
    col_dim may be a multi-value field (hazards, life_saving_rules, barrier_failures).
    """
    df2 = df.copy()
    df2["sif_risk_score_num"] = pd.to_numeric(df2["sif_risk_score"], errors="coerce").fillna(0)

    records = []
    for _, row in df2.iterrows():
        row_val = str(row.get(row_dim, "Unknown")).strip() or "Unknown"
        col_vals = _parse_list(row[col_dim]) if col_dim in row else [str(row.get(col_dim, "Unknown"))]
        score = float(row.get("sif_risk_score_num", 0))
        for cv in col_vals[:3]:
            records.append({
                "row": row_val,
                "col": cv,
                "score": score,
            })

    if not records:
        return {"rows": [], "cols": [], "matrix": []}

    hm_df = pd.DataFrame(records)
    pivot = hm_df.groupby(["row", "col"])["score"].mean().unstack(fill_value=0).round(1)

    # Limit dimensions for readability
    top_rows = (
        hm_df.groupby("row")["score"].mean().nlargest(10).index.tolist()
    )
    top_cols = (
        hm_df.groupby("col")["score"].mean().nlargest(8).index.tolist()
    )

    pivot = pivot.reindex(index=top_rows, columns=top_cols, fill_value=0)

    return {
        "rows": pivot.index.tolist(),
        "cols": pivot.columns.tolist(),
        "matrix": pivot.values.tolist(),
    }


# ─── SIF Risk Distribution ────────────────────────────────────────────────────

def get_sif_risk_distribution(df: pd.DataFrame) -> List[Dict]:
    df2 = df.copy()
    df2["score_num"] = pd.to_numeric(df2["sif_risk_score"], errors="coerce").fillna(0)
    bins = [0, 20, 40, 60, 70, 80, 90, 101]
    labels = ["0-20", "21-40", "41-60", "61-70", "71-80", "81-90", "91-100"]
    df2["bucket"] = pd.cut(df2["score_num"], bins=bins, labels=labels, right=False)
    counts = df2["bucket"].value_counts().sort_index().reset_index()
    counts.columns = ["range", "count"]
    return counts.to_dict("records")


# ─── Filters ─────────────────────────────────────────────────────────────────

def apply_filters(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """Apply dashboard filters to DataFrame."""
    df2 = df.copy()

    if filters.get("site"):
        df2 = df2[df2["site"] == filters["site"]]

    if filters.get("source"):
        df2 = df2[df2["source"] == filters["source"]]

    if filters.get("sif_label"):
        df2 = df2[df2["sif_label"] == filters["sif_label"]]

    if filters.get("actual_severity"):
        df2 = df2[df2["actual_severity"] == filters["actual_severity"]]

    if filters.get("activity"):
        df2 = df2[df2["activity"].str.lower().str.contains(
            filters["activity"].lower(), na=False
        )]

    if filters.get("date_from"):
        df2 = df2[
            pd.to_datetime(df2["report_date"], errors="coerce")
            >= pd.to_datetime(filters["date_from"])
        ]

    if filters.get("date_to"):
        df2 = df2[
            pd.to_datetime(df2["report_date"], errors="coerce")
            <= pd.to_datetime(filters["date_to"])
        ]

    if filters.get("min_sif_score") is not None:
        df2 = df2[
            pd.to_numeric(df2["sif_risk_score"], errors="coerce").fillna(0)
            >= int(filters["min_sif_score"])
        ]

    return df2


if __name__ == "__main__":
    from data_pipeline import run_pipeline
    df = run_pipeline()
    kpi = get_kpi_summary(df)
    print("KPIs:", kpi)
