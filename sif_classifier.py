"""
SIF Classifier & Risk Scoring Engine
Phase 2–3: Baseline TF-IDF + Logistic Regression → SIF label, probability, risk score
Separates ACTUAL severity from POTENTIAL consequence (Phase 4)
"""

import sys
import json
import re
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
import joblib

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import (
    SIF_THRESHOLDS, SEVERITY_WEIGHTS, MODELS_DIR,
    LIFE_SAVING_RULE_KEYWORDS, HAZARD_KEYWORDS,
)


# ─── SIF Labeling Strategy ───────────────────────────────────────────────────
# We distinguish ACTUAL outcome from POTENTIAL consequence
# SIF potential is about fatal/severe injury *possibility*, not what happened

# Phrases strongly associated with SIF potential
SIF_HIGH_SIGNALS = [
    # Energy / isolation failures
    "without verifying isolation", "not de-energized", "not de-energised",
    "energized during", "energised during", "without lockout", "without loto",
    "live equipment", "live panel", "live wire", "arc flash",
    # Pressure / release
    "residual pressure", "stored pressure", "stored energy", "overpressure",
    "pressurized line", "pressurised line", "hydrocarbon release", "gas cloud",
    "flammable gas", "gas ignition", "explosion",
    # Confined space
    "confined space without", "no atmospheric testing", "no gas test",
    "without testing", "h2s", "hydrogen sulphide", "oxygen deficiency",
    # Height
    "working at height without", "no fall arrest", "no harness",
    "without fall protection", "without harness",
    # Line of fire / struck
    "line of fire", "struck by", "no exclusion zone", "under a load",
    "suspended load", "overhead load", "falling load",
    # Well control
    "blowout", "well kick", "bop failure", "well pressure surge",
    # Hot work
    "hot work without permit", "no fire watch", "near flammable",
    "near combustible", "ignition source",
    # Fatal / severe outcome
    "fatally injured", "fatal", "death", "killed",
    # Near miss with high potential
    "could have been fatal", "potential fatality", "potentially fatal",
    "near fatal", "near-fatal",
]

SIF_MEDIUM_SIGNALS = [
    "without ppe", "no ppe", "without permit", "no permit",
    "without training", "unqualified", "bypass", "bypassed",
    "override", "disabled safety", "safety system disabled",
    "procedure not followed", "fell", "fall", "collapse",
    "toxic", "chemical burn", "burns",
    "incorrect isolation", "wrong isolation point",
]

NON_SIF_SIGNALS = [
    "minor cut", "minor scratch", "small bruise", "sprained",
    "housekeeping", "slipped on wet floor minor",
    "near miss - administrative", "paperwork",
]

# Potential consequence logic
FATAL_POTENTIAL_KEYWORDS = [
    "energized", "energised", "h2s", "hydrogen sulphide",
    "confined space", "line of fire", "suspended load", "residual pressure",
    "without isolation", "no lockout", "blowout", "explosion", "fire",
    "working at height without", "no fall arrest", "fatally",
    "fatal", "gas cloud", "flammable atmosphere",
]

POTENTIAL_CONSEQUENCE_MAP = {
    "Fatal": [
        "fatal", "fatally", "death", "killed", "energized without isolation",
        "energised without isolation", "h2s exposure", "line of fire",
        "suspended load no exclusion", "well blowout", "explosion",
        "confined space without atmospheric", "gas cloud ignit",
    ],
    "SIF-Capable": [
        "residual pressure", "stored energy", "working at height without harness",
        "no gas test confined", "no loto", "no lockout", "bypass safety",
        "override interlock", "without permit", "hot work near flammable",
        "struck by vehicle", "no exclusion zone lift",
    ],
    "Serious": [
        "hospitalized", "hospitalized", "burns", "fracture", "severe",
        "chemical exposure", "without ppe", "fall arrest not",
        "procedure not followed",
    ],
    "Moderate": [
        "medical treatment", "minor", "first aid", "near miss", "small",
    ],
    "Low": [
        "no hazard", "administrative", "housekeeping",
    ],
}


# ─── Heuristic SIF Labeler ────────────────────────────────────────────────────

def heuristic_sif_label(row: pd.Series) -> Dict:
    """
    Assign a heuristic SIF label, probability estimate, and potential consequence.
    Separates ACTUAL outcome from POTENTIAL consequence.
    """
    text = str(row.get("clean_text", "")).lower()
    actual_severity = str(row.get("actual_severity", "")).lower()

    # ── Actual severity score (0-1) ──
    sev_weight = SEVERITY_WEIGHTS.get(
        row.get("actual_severity", "Unknown"), 0.2
    )

    # ── Count SIF signal hits ──
    high_hits = sum(1 for s in SIF_HIGH_SIGNALS if s in text)
    med_hits = sum(1 for s in SIF_MEDIUM_SIGNALS if s in text)
    non_sif_hits = sum(1 for s in NON_SIF_SIGNALS if s in text)

    # ── Potential consequence ──
    potential_consequence = _classify_potential_consequence(text, row)

    # ── Fatal potential flag ──
    fatal_hit = any(k in text for k in FATAL_POTENTIAL_KEYWORDS)
    actual_fatal = "fatal" in actual_severity or "death" in actual_severity

    # ── Composite score (0-100 range internal) ──
    raw_score = (
        high_hits * 18
        + med_hits * 8
        + sev_weight * 30
        + (20 if fatal_hit else 0)
        + (15 if actual_fatal else 0)
        - non_sif_hits * 15
    )
    raw_score = max(0, min(100, raw_score))

    # ── SIF label ──
    if raw_score >= 65 or actual_fatal or potential_consequence == "Fatal":
        sif_label = "High-Confidence SIF"
        sif_probability = min(0.75 + high_hits * 0.04, 0.97)
    elif raw_score >= 35 or potential_consequence in ("SIF-Capable", "Serious"):
        sif_label = "Potential SIF"
        sif_probability = 0.45 + high_hits * 0.05
    else:
        sif_label = "Non-SIF"
        sif_probability = max(0.05, 0.25 - non_sif_hits * 0.05)

    sif_risk_score = int(raw_score)

    return {
        "sif_label": sif_label,
        "sif_probability": round(float(sif_probability), 3),
        "sif_risk_score": sif_risk_score,
        "potential_consequence": potential_consequence,
        "fatal_potential": fatal_hit or actual_fatal,
        "label_source": "heuristic",
    }


def _classify_potential_consequence(text: str, row: pd.Series) -> str:
    """Determine the credible worst-case consequence from the text."""
    actual = str(row.get("actual_severity", "")).lower()

    for level, keywords in POTENTIAL_CONSEQUENCE_MAP.items():
        if any(k in text for k in keywords):
            return level

    # Fall back to actual severity
    if "fatal" in actual:
        return "Fatal"
    if "hospitali" in actual or "severe" in actual:
        return "SIF-Capable"
    if "medical" in actual or "lost time" in actual:
        return "Serious"
    if "first aid" in actual or "near miss" in actual or "no injury" in actual:
        return "Moderate"
    return "Low"


# ─── TF-IDF + LR Classifier ───────────────────────────────────────────────────

class SIFClassifier:
    """
    Stage 1: TF-IDF + Logistic Regression baseline.
    Trained on heuristic-labeled data where no ground truth exists.
    """

    def __init__(self):
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=8000,
                min_df=1,
                sublinear_tf=True,
                stop_words="english",
            )),
            ("clf", LogisticRegression(
                C=1.0,
                class_weight="balanced",   # Handle imbalance explicitly
                max_iter=500,
                random_state=42,
            )),
        ])
        self.label_encoder = LabelEncoder()
        self.trained = False

    def fit(self, texts: List[str], labels: List[str]) -> "SIFClassifier":
        encoded = self.label_encoder.fit_transform(labels)
        self.pipeline.fit(texts, encoded)
        self.trained = True
        return self

    def predict_proba_labeled(self, texts: List[str]) -> List[Dict]:
        if not self.trained:
            raise RuntimeError("Classifier not trained.")
        proba = self.pipeline.predict_proba(texts)
        classes = self.label_encoder.classes_
        results = []
        for p in proba:
            label_idx = int(np.argmax(p))
            results.append({
                "predicted_label": classes[label_idx],
                "confidence": float(round(p[label_idx], 3)),
                "class_probabilities": {
                    classes[i]: float(round(p[i], 3)) for i in range(len(classes))
                },
            })
        return results

    def evaluate(self, texts: List[str], true_labels: List[str]) -> Dict:
        encoded_true = self.label_encoder.transform(true_labels)
        encoded_pred = self.pipeline.predict(texts)
        report = classification_report(
            encoded_true, encoded_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True,
        )
        cm = confusion_matrix(encoded_true, encoded_pred)
        return {
            "classification_report": report,
            "confusion_matrix": cm.tolist(),
            "classes": list(self.label_encoder.classes_),
        }

    def save(self, path: Path = MODELS_DIR) -> None:
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, path / "sif_pipeline.pkl")
        joblib.dump(self.label_encoder, path / "label_encoder.pkl")

    def load(self, path: Path = MODELS_DIR) -> "SIFClassifier":
        self.pipeline = joblib.load(path / "sif_pipeline.pkl")
        self.label_encoder = joblib.load(path / "label_encoder.pkl")
        self.trained = True
        return self


# ─── Explainability ───────────────────────────────────────────────────────────

def generate_explanation(text: str, sif_result: Dict, extracted: Dict) -> List[str]:
    """
    Generate traceable human-readable explanation.
    Each line is anchored to an extracted field or text signal.
    """
    lines = []
    text_lower = text.lower()

    # Potential consequence
    pc = sif_result.get("potential_consequence", "")
    if pc in ("Fatal", "SIF-Capable"):
        lines.append(
            f"The report describes a scenario with credible {pc.lower()} potential "
            "even if no serious injury occurred."
        )

    # Barrier failures
    failures = extracted.get("barrier_failures", [])
    if failures:
        lines.append(f"Critical barrier failures identified: {', '.join(failures)}.")

    # Missing barriers
    missing = extracted.get("barriers_missing", [])
    if missing:
        lines.append(f"Required controls were absent: {', '.join(missing)}.")

    # Hazards
    hazards = extracted.get("hazards", [])
    if hazards and hazards != ["Unknown"]:
        lines.append(f"Hazard(s) present: {', '.join(hazards)}.")

    # Life-Saving Rules
    lsr = extracted.get("life_saving_rules", [])
    if lsr:
        lines.append(f"Applicable Life-Saving Rule(s): {', '.join(lsr)}.")

    # Specific high-signal phrases found
    found_signals = [s for s in SIF_HIGH_SIGNALS if s in text_lower]
    for sig in found_signals[:3]:
        # Find the sentence containing this signal
        for sent in re.split(r"(?<=[.!?])\s+", text):
            if sig in sent.lower():
                lines.append(f'Key indicator: "{sent.strip()}"')
                break

    # Contributing factors
    factors = extracted.get("contributing_factors", [])
    if factors:
        lines.append(f"AI-suggested contributing factors: {', '.join(factors[:3])}.")

    # Score rationale
    score = sif_result.get("sif_risk_score", 0)
    label = sif_result.get("sif_label", "")
    if score >= 70:
        lines.append(
            f"Risk score {score}/100 reflects multiple concurrent failures creating "
            "conditions for a serious or fatal outcome."
        )
    elif score >= 40:
        lines.append(
            f"Risk score {score}/100 reflects identifiable SIF precursors that warrant "
            "preventive action."
        )

    if not lines:
        lines.append("Insufficient detail in the report to generate a specific explanation.")

    return lines


# ─── Evidence Spans ───────────────────────────────────────────────────────────

def highlight_evidence(text: str) -> List[Dict]:
    """
    Return annotated evidence spans linking text fragments to risk categories.
    """
    spans = []
    text_lower = text.lower()

    from config.settings import BARRIER_TAXONOMY, HAZARD_KEYWORDS

    for barrier, keywords in BARRIER_TAXONOMY.items():
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                start = max(0, idx - 15)
                end = min(len(text), idx + len(kw) + 30)
                snippet = text[start:end].strip()
                # Check context
                window = text_lower[max(0, idx-40):idx+60]
                from backend.services.nlp_extractor import FAILURE_PHRASES
                if any(fp in window for fp in FAILURE_PHRASES):
                    category = "Barrier Failure"
                else:
                    category = "Barrier Present"
                spans.append({
                    "text": snippet,
                    "category": category,
                    "matched_control": barrier,
                })
                break

    for hazard, keywords in HAZARD_KEYWORDS.items():
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                start = max(0, idx - 10)
                end = min(len(text), idx + len(kw) + 40)
                snippet = text[start:end].strip()
                spans.append({
                    "text": snippet,
                    "category": "Hazard",
                    "matched_control": hazard,
                })
                break

    return spans[:8]


# ─── Full Analysis Entry Point ────────────────────────────────────────────────

def analyze_report(row: pd.Series, extracted: Optional[Dict] = None) -> Dict:
    """
    Combine heuristic SIF labeling + explanation for one report.
    `extracted` is the output of nlp_extractor.extract_all()
    """
    if extracted is None:
        from backend.services.nlp_extractor import extract_all
        extracted = extract_all(str(row.get("clean_text", "")))

    sif_result = heuristic_sif_label(row)
    text = str(row.get("clean_text", ""))
    explanation = generate_explanation(text, sif_result, extracted)
    evidence_spans = highlight_evidence(text)

    return {
        **sif_result,
        "explanation": explanation,
        "evidence_spans": evidence_spans,
        "actual_severity": row.get("actual_severity", "Unknown"),
        "actual_outcome": row.get("actual_outcome", ""),
        **{k: v for k, v in extracted.items()},
    }


if __name__ == "__main__":
    sample = pd.Series({
        "clean_text": (
            "Worker began maintenance on electrical equipment without verifying isolation. "
            "The equipment remained energized during the task. "
            "A supervisor later noted the lockout procedure was not followed."
        ),
        "actual_severity": "Severe Injury",
        "actual_outcome": "No Fatality",
        "site": "Site_A",
        "activity": "Electrical Maintenance",
    })
    result = analyze_report(sample)
    print("SIF Label:", result["sif_label"])
    print("SIF Score:", result["sif_risk_score"])
    print("Potential:", result["potential_consequence"])
    print("Hazards:", result["hazards"])
    print("Barriers Failed:", result["barrier_failures"])
    print("LSR:", result["life_saving_rules"])
    print("Explanation:")
    for line in result["explanation"]:
        print(" -", line)
