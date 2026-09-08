"""
NLP Feature & Entity Extraction
Extracts: hazards, barriers (present/failed/missing), activities,
          unsafe acts, unsafe conditions, contributing factors
Uses: rule/dictionary baseline + context scoring
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import (
    HAZARD_TAXONOMY, HAZARD_KEYWORDS,
    BARRIER_TAXONOMY, LIFE_SAVING_RULES, LIFE_SAVING_RULE_KEYWORDS
)


# ─── Sentinel phrases ────────────────────────────────────────────────────────

FAILURE_PHRASES = [
    "not in place", "not followed", "not verified", "not confirmed", "not present",
    "not worn", "not obtained", "not conducted", "not performed", "not established",
    "no permit", "no gas test", "no harness", "no guard", "no isolation",
    "removed", "bypassed", "disabled", "gagged", "override", "inhibited",
    "without", "absent", "missing", "failed", "failure", "inadequate",
    "not available", "unavailable", "not done", "not completed",
]

PRESENT_PHRASES = [
    "in place", "verified", "followed", "conducted", "worn",
    "obtained", "present", "established", "applied",
]

UNSAFE_ACT_PHRASES = [
    "worker did not", "worker failed", "worker entered without", "worker was",
    "employee did", "technician did", "observed worker", "worker operating",
    "without wearing", "without confirming", "without obtaining", "entered without",
    "did not use", "bypassed", "operated without",
]

CONTRIBUTING_PATTERNS = {
    "Procedure Not Followed": [
        "procedure not followed", "did not follow procedure", "failed to follow",
        "not in accordance", "contrary to procedure", "ignoring procedure",
    ],
    "Procedure Missing": [
        "no procedure", "procedure not available", "no documented procedure",
        "procedure was absent", "no work instruction",
    ],
    "Inadequate Risk Assessment": [
        "risk not assessed", "no risk assessment", "inadequate risk assessment",
        "hazard not identified", "risk not recognised",
    ],
    "Permit Failure": [
        "no permit", "permit not obtained", "permit not in place",
        "work without permit", "no work permit", "permit was not issued",
        "no hot work permit", "no entry permit",
    ],
    "Inadequate Supervision": [
        "no supervisor", "unsupervised", "supervisor not present",
        "lack of supervision", "insufficient oversight",
    ],
    "Communication Failure": [
        "not communicated", "failed to communicate", "no communication",
        "not informed", "not notified",
    ],
    "Inadequate Competence": [
        "not trained", "untrained", "not certified", "not qualified",
        "without induction", "not authorized", "not authorised",
    ],
    "Equipment Failure": [
        "equipment failed", "equipment fault", "sling failure", "seal failure",
        "valve failure", "instrument failure", "device failure",
    ],
    "Isolation Failure": [
        "isolation not verified", "wrong isolation", "isolation not confirmed",
        "isolation not completed", "incomplete isolation", "no lockout",
        "no loto", "not de-energized", "not de-energised",
    ],
    "Management of Change Failure": [
        "no management of change", "no moc", "unauthorized change",
        "without approval", "no change authorization",
    ],
    "Inadequate Planning": [
        "not planned", "no lift plan", "no job hazard analysis", "no jha",
        "no pre-task planning", "no toolbox talk",
    ],
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _lower(text: str) -> str:
    return text.lower() if isinstance(text, str) else ""


def _keyword_match(text_lower: str, keywords: List[str]) -> bool:
    return any(kw in text_lower for kw in keywords)


def _find_evidence_spans(text: str, keywords: List[str]) -> List[str]:
    """Return sentence-level spans that contain any keyword."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    spans = []
    for s in sentences:
        if any(kw in s.lower() for kw in keywords):
            spans.append(s.strip())
    return spans[:3]  # cap for readability


# ─── Hazard Extraction ───────────────────────────────────────────────────────

def extract_hazards(text: str) -> Tuple[List[str], List[str]]:
    """Return (hazard_list, evidence_spans)."""
    t = _lower(text)
    found = []
    spans = []
    for hazard, keywords in HAZARD_KEYWORDS.items():
        if _keyword_match(t, keywords):
            found.append(hazard)
            spans.extend(_find_evidence_spans(text, keywords))
    if not found:
        found = ["Unknown"]
    return list(dict.fromkeys(found)), list(dict.fromkeys(spans))[:4]


# ─── Barrier Extraction ───────────────────────────────────────────────────────

def extract_barriers(text: str) -> Dict[str, List[str]]:
    """
    Returns dict with:
      present  - barriers mentioned as being in place
      failed   - barriers that failed / were breached
      missing  - barriers that were absent / not used
    """
    t = _lower(text)
    result = {"present": [], "failed": [], "missing": []}

    for barrier, keywords in BARRIER_TAXONOMY.items():
        if not _keyword_match(t, keywords):
            continue
        # Check context around the keyword hit
        for kw in keywords:
            idx = t.find(kw)
            if idx == -1:
                continue
            window = t[max(0, idx - 60): idx + 80]
            is_failed = _keyword_match(window, FAILURE_PHRASES)
            is_present = _keyword_match(window, PRESENT_PHRASES)

            if is_failed:
                if barrier not in result["failed"]:
                    result["failed"].append(barrier)
            elif is_present:
                if barrier not in result["present"]:
                    result["present"].append(barrier)
            else:
                # If keyword present but no strong context, check negation at sentence level
                spans = _find_evidence_spans(text, [kw])
                for span in spans:
                    if _keyword_match(span.lower(), ["not ", "no ", "without ", "absent", "missing"]):
                        if barrier not in result["missing"]:
                            result["missing"].append(barrier)
                        break
                    else:
                        if barrier not in result["present"]:
                            result["present"].append(barrier)
    return result


# ─── Life-Saving Rule Mapping ─────────────────────────────────────────────────

def map_life_saving_rules(text: str) -> List[Dict]:
    """Return list of {rule, confidence, evidence}."""
    t = _lower(text)
    results = []
    for rule, keywords in LIFE_SAVING_RULE_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in t]
        if not matches:
            continue
        confidence = min(0.5 + 0.1 * len(matches), 0.97)
        evidence = _find_evidence_spans(text, keywords)
        results.append({
            "rule": rule,
            "confidence": round(confidence, 2),
            "evidence": evidence[:2],
            "match_count": len(matches),
        })
    results.sort(key=lambda x: -x["confidence"])
    return results


# ─── Contributing Factors ─────────────────────────────────────────────────────

def extract_contributing_factors(text: str) -> List[Dict]:
    """Return AI-suggested contributing factors with confidence."""
    t = _lower(text)
    factors = []
    for factor, phrases in CONTRIBUTING_PATTERNS.items():
        matched = [p for p in phrases if p in t]
        if matched:
            confidence = min(0.4 + 0.15 * len(matched), 0.92)
            factors.append({
                "factor": factor,
                "confidence": round(confidence, 2),
                "evidence": matched[:2],
            })
    factors.sort(key=lambda x: -x["confidence"])
    return factors


# ─── Unsafe Acts / Conditions ─────────────────────────────────────────────────

def extract_unsafe_acts(text: str) -> List[str]:
    t = _lower(text)
    acts = []
    for phrase in UNSAFE_ACT_PHRASES:
        if phrase in t:
            idx = t.find(phrase)
            snippet = text[idx: idx + 120].split(".")[0]
            acts.append(snippet.strip())
    return list(dict.fromkeys(acts))[:4]


def extract_unsafe_conditions(text: str) -> List[str]:
    conditions_patterns = [
        r"no\s+(?:guard|barrier|protection|isolation|monitoring|permit|testing)\b",
        r"(?:guard|barrier|protection)\s+(?:was\s+)?(?:removed|absent|missing|not present)",
        r"equipment\s+(?:was\s+)?(?:energized|energised|pressurized|pressurised)",
        r"unshored excavation",
        r"live\s+(?:panel|wire|equipment|circuit)",
        r"bypass(?:ed)?\s+(?:safety|interlock|alarm)",
    ]
    found = []
    for pat in conditions_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            snippet = text[max(0, m.start() - 20): m.end() + 50].strip()
            found.append(snippet)
    return list(dict.fromkeys(found))[:4]


# ─── Full Extraction ──────────────────────────────────────────────────────────

def extract_all(text: str) -> Dict:
    """Run all extractors and return combined structured output."""
    hazards, hazard_evidence = extract_hazards(text)
    barriers = extract_barriers(text)
    lsr = map_life_saving_rules(text)
    factors = extract_contributing_factors(text)
    unsafe_acts = extract_unsafe_acts(text)
    unsafe_conditions = extract_unsafe_conditions(text)

    return {
        "hazards": hazards,
        "hazard_evidence": hazard_evidence,
        "barriers_present": barriers["present"],
        "barriers_missing": barriers["missing"],
        "barrier_failures": barriers["failed"],
        "life_saving_rules": [r["rule"] for r in lsr],
        "life_saving_rule_details": lsr,
        "contributing_factors": [f["factor"] for f in factors],
        "contributing_factor_details": factors,
        "unsafe_acts": unsafe_acts,
        "unsafe_conditions": unsafe_conditions,
    }


if __name__ == "__main__":
    test_text = (
        "Worker began maintenance on electrical equipment without verifying isolation. "
        "The equipment remained energized during the task. A supervisor later noted "
        "the lockout procedure was not followed. No permit to work was obtained."
    )
    result = extract_all(test_text)
    for k, v in result.items():
        print(f"{k}: {v}")
