"""
SIF Platform Configuration
All thresholds, taxonomies, and model settings are centralized here.
"""

import os
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models" / "artifacts"
CONFIG_DIR = BASE_DIR / "config"

RAW_DATA_PATH = DATA_DIR / "raw" / "sample_reports.csv"
PROCESSED_DATA_PATH = DATA_DIR / "processed" / "master_dataset.csv"
EMBEDDINGS_PATH = DATA_DIR / "embeddings"

# ─── SIF Risk Score Thresholds ───────────────────────────────────────────────
# These are prototype defaults — not OIL policy
SIF_THRESHOLDS = {
    "CRITICAL": 90,
    "HIGH": 70,
    "MEDIUM": 40,
    "LOW": 0,
}

# ─── Actual Severity Levels ──────────────────────────────────────────────────
ACTUAL_SEVERITY_LEVELS = [
    "No Injury",
    "First Aid",
    "Medical Treatment",
    "Lost Time",
    "Hospitalized",
    "Severe Injury",
    "Fatality",
    "Unknown",
]

SEVERITY_WEIGHTS = {
    "No Injury": 0.0,
    "First Aid": 0.1,
    "Medical Treatment": 0.3,
    "Lost Time": 0.4,
    "Hospitalized": 0.6,
    "Severe Injury": 0.75,
    "Fatality": 1.0,
    "Unknown": 0.2,
    "Near Miss": 0.05,
    "Minor": 0.1,
    "Moderate": 0.35,
    "Major Incident": 0.7,
    "Fatal": 1.0,
    "Severe": 0.75,
}

# ─── SIF Potential Labels ────────────────────────────────────────────────────
SIF_POTENTIAL_LABELS = ["Non-SIF", "Potential SIF", "High-Confidence SIF"]

# ─── IOGP Life-Saving Rules ──────────────────────────────────────────────────
# Configurable taxonomy — replace with OIL's officially preferred taxonomy
LIFE_SAVING_RULES = [
    "Energy Isolation",
    "Confined Space",
    "Hot Work",
    "Line of Fire",
    "Working at Height",
    "Lifting Operations",
    "Driving / Vehicle Safety",
    "Well / Pressure Control",
    "Excavation / Ground Disturbance",
    "Bypassing Safety Systems",
]

# Keywords per rule for heuristic mapping (seed rules)
LIFE_SAVING_RULE_KEYWORDS = {
    "Energy Isolation": [
        "lockout", "loto", "isolation", "de-energi", "energized", "energised",
        "lock out", "tag out", "isolate", "energy control", "electrical isolation",
        "pressure isolation", "zero energy", "stored energy", "isolation not verified",
        "work on live", "live equipment",
    ],
    "Confined Space": [
        "confined space", "manhole", "vessel", "tank entry", "sewer", "pit",
        "atmospheric testing", "gas testing", "oxygen deficiency", "oxygen level",
        "h2s in confined", "entry without permit", "confined space entry",
    ],
    "Hot Work": [
        "hot work", "welding", "grinding", "cutting", "spark", "open flame",
        "soldering", "thermal cutting", "hot work permit", "fire watch",
        "combustible gas", "flammable atmosphere",
    ],
    "Line of Fire": [
        "line of fire", "struck by", "in the path", "exclusion zone", "drop zone",
        "under load", "suspended load", "path of travel", "struck", "ejected",
        "projectile", "spray", "release direction",
    ],
    "Working at Height": [
        "working at height", "fall", "fell", "falling", "height", "elevated",
        "ladder", "scaffold", "platform", "roof", "harness", "fall arrest",
        "fall protection", "edge protection", "lifeline",
    ],
    "Lifting Operations": [
        "crane", "lift", "lifting", "rigging", "sling", "suspended", "overhead",
        "hoist", "forklift", "lift plan", "rated capacity", "slinging",
    ],
    "Driving / Vehicle Safety": [
        "vehicle", "driving", "driver", "reversing", "pedestrian", "heavy vehicle",
        "forklift", "mobile plant", "spotter", "transport", "road", "collision",
    ],
    "Well / Pressure Control": [
        "well", "blowout", "bop", "well control", "well pressure", "kick",
        "pressure surge", "well integrity", "wellhead", "production tubing",
    ],
    "Excavation / Ground Disturbance": [
        "excavation", "trench", "excavate", "digging", "underground", "shoring",
        "benching", "ground collapse", "buried", "third party excavation",
    ],
    "Bypassing Safety Systems": [
        "bypass", "bypassing", "override", "defeat", "interlock", "inhibit",
        "gagged", "disabled", "safety system", "alarm bypass", "sis bypass",
        "management of change", "unauthorized",
    ],
}

# ─── Hazard Taxonomy ─────────────────────────────────────────────────────────
HAZARD_TAXONOMY = [
    "Electrical Energy",
    "Stored Pressure / Energy",
    "Hydrocarbon Release",
    "Toxic Gas (H2S)",
    "Flammable Gas / Vapour",
    "Fire / Explosion",
    "Chemical Exposure",
    "Confined Space Atmosphere",
    "Fall from Height",
    "Suspended / Falling Load",
    "Vehicle / Mobile Equipment",
    "Line of Fire / Projectile",
    "Rotating / Moving Equipment",
    "Hot Work / Ignition Source",
    "Excavation Collapse",
    "Radiation",
    "Environmental",
    "Well / Pressure Blowout",
    "Other",
    "Unknown",
]

HAZARD_KEYWORDS = {
    "Electrical Energy": [
        "electric", "electrical", "energized", "energised", "live wire",
        "arc flash", "shock", "voltage", "switchboard", "live panel", "high voltage",
    ],
    "Stored Pressure / Energy": [
        "pressure", "pressurized", "residual pressure", "stored energy",
        "pneumatic", "hydraulic", "compressed", "depressurise", "blowdown",
        "overpressure",
    ],
    "Hydrocarbon Release": [
        "hydrocarbon", "oil release", "gas release", "hydrocarbon spray",
        "flange leak", "seal failure", "crude oil", "product release",
    ],
    "Toxic Gas (H2S)": [
        "h2s", "hydrogen sulphide", "hydrogen sulfide", "toxic gas", "sour gas",
        "gas exposure", "gas cloud",
    ],
    "Flammable Gas / Vapour": [
        "flammable", "combustible gas", "gas cloud", "vapour", "vapor",
        "methane", "lpg", "natural gas", "ignition",
    ],
    "Fire / Explosion": [
        "fire", "explosion", "blast", "flash fire", "ignition", "burn",
        "combustion", "deflagration", "detonation",
    ],
    "Chemical Exposure": [
        "chemical", "acid", "corrosive", "methanol", "chemical burn",
        "toxic chemical", "chemical splash", "chemical spray",
    ],
    "Confined Space Atmosphere": [
        "oxygen deficiency", "oxygen depletion", "toxic atmosphere",
        "atmospheric testing", "confined space", "gas test", "h2s in confined",
    ],
    "Fall from Height": [
        "fall", "fell", "falling", "height", "ladder", "scaffold",
        "elevated", "roof", "platform", "edge",
    ],
    "Suspended / Falling Load": [
        "suspended load", "overhead load", "dropped object", "falling object",
        "crane load", "rigging failure", "sling failure",
    ],
    "Vehicle / Mobile Equipment": [
        "vehicle", "forklift", "heavy vehicle", "mobile plant",
        "reversing", "struck by vehicle", "road accident",
    ],
    "Line of Fire / Projectile": [
        "line of fire", "struck by", "ejected", "projectile", "fragment",
        "flying object", "impact", "spray direction",
    ],
    "Rotating / Moving Equipment": [
        "rotating", "machinery", "press", "conveyor", "pinch point",
        "moving part", "equipment in motion",
    ],
    "Hot Work / Ignition Source": [
        "hot work", "welding", "grinding", "spark", "open flame",
        "ignition source", "cutting",
    ],
    "Excavation Collapse": [
        "excavation", "trench collapse", "wall collapse", "buried",
        "ground collapse", "cave in",
    ],
    "Well / Pressure Blowout": [
        "blowout", "well kick", "bop", "well surge", "well pressure",
        "blowout preventer",
    ],
}

# ─── Barrier / Control Taxonomy ──────────────────────────────────────────────
BARRIER_TAXONOMY = {
    "LOTO / Energy Isolation": [
        "lockout", "tagout", "loto", "energy isolation", "isolation verified",
        "isolation point", "de-energized", "lock", "tag",
    ],
    "Permit to Work": [
        "permit", "work permit", "hot work permit", "entry permit",
        "permit to work", "ptw",
    ],
    "Atmospheric Monitoring": [
        "gas test", "atmospheric testing", "gas detector", "oxygen test",
        "gas monitoring", "h2s detector", "continuous monitoring",
    ],
    "Guarding / Barricading": [
        "guard", "guarding", "barrier", "barricade", "exclusion zone",
        "restricted area", "drop zone",
    ],
    "Fall Protection": [
        "harness", "fall arrest", "lifeline", "edge protection",
        "fall protection", "lanyard", "anchor point",
    ],
    "PPE": [
        "ppe", "personal protective equipment", "gloves", "face shield",
        "safety glasses", "respirator", "protective clothing",
    ],
    "Pressure Relief / ESD": [
        "pressure relief", "relief valve", "emergency shutdown", "esd",
        "safety valve", "psv", "pressure safety",
    ],
    "Competency / Training": [
        "competent", "training", "qualified", "certified", "induction",
        "authorized", "authorised",
    ],
    "Supervision": [
        "supervisor", "supervision", "oversight", "second person", "standby",
        "spotter",
    ],
    "Procedure / Safe Work Method": [
        "procedure", "work instruction", "safe work", "method statement",
        "checklist", "toolbox talk",
    ],
    "Management of Change": [
        "management of change", "moc", "change management", "authorization",
        "approval", "bypass permit",
    ],
    "Vehicle Segregation": [
        "pedestrian segregation", "traffic management", "segregation",
        "vehicle exclusion", "pedestrian route",
    ],
}

# ─── Risk Score Weights ──────────────────────────────────────────────────────
# Adjustable for operational context
RISK_SCORE_WEIGHTS = {
    "potential_severity": 0.30,
    "barrier_failure_count": 0.25,
    "hazard_criticality": 0.20,
    "worker_proximity": 0.10,
    "repeat_precursor": 0.10,
    "actual_severity": 0.05,
}

# ─── Pattern Detection ───────────────────────────────────────────────────────
MIN_PATTERN_SUPPORT = 2          # Minimum reports per pattern
SIMILARITY_THRESHOLD = 0.72      # Cosine similarity threshold for similar incidents
TOP_K_SIMILAR = 5                # Number of similar incidents to return

# ─── Model Settings ──────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # Lightweight, good quality
MODEL_VERSION = "v1.0-prototype"
