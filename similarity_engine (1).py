"""
Embedding & Similar Incident Search Engine
Phase 8: sentence-transformers → FAISS index → nearest-neighbor retrieval
"""

import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.settings import (
    EMBEDDING_MODEL, EMBEDDINGS_PATH,
    SIMILARITY_THRESHOLD, TOP_K_SIMILAR,
)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False


class SimilarityEngine:
    """
    Semantic similarity search over safety reports.
    Uses sentence-transformers for embeddings and FAISS for ANN search.
    Falls back to cosine similarity with numpy if FAISS unavailable.
    """

    def __init__(self):
        self.model = None
        self.index = None
        self.report_ids: List[str] = []
        self.df_metadata: Optional[pd.DataFrame] = None
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_dim = 384  # MiniLM default

    def load_model(self) -> None:
        if not ST_AVAILABLE:
            print("[Similarity] sentence-transformers not available — using TF-IDF similarity (demo)")
            return
        try:
            print(f"[Similarity] Loading model: {EMBEDDING_MODEL}")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            print(f"[Similarity] Model loaded. Dim={self.embedding_dim}")
        except Exception as e:
            print(f"[Similarity] Model load failed ({e}) — using TF-IDF similarity fallback")
            self.model = None

    def encode(self, texts: List[str]) -> np.ndarray:
        if self.model is None:
            return self._tfidf_encode(texts)
        return self.model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    def _tfidf_encode(self, texts: List[str]) -> np.ndarray:
        """TF-IDF based fallback encoding — good for keyword-rich safety reports."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        if not hasattr(self, "_tfidf_vectorizer") or self._tfidf_vectorizer is None:
            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=self.embedding_dim,
                ngram_range=(1, 2),
                sublinear_tf=True,
                stop_words="english",
            )
            if hasattr(self, "_corpus_texts") and self._corpus_texts:
                all_texts = list(set(self._corpus_texts + texts))
                self._tfidf_vectorizer.fit(all_texts)
            else:
                self._tfidf_vectorizer.fit(texts)
        matrix = self._tfidf_vectorizer.transform(texts).toarray().astype(np.float32)
        # Pad or truncate to embedding_dim
        if matrix.shape[1] < self.embedding_dim:
            padding = np.zeros((matrix.shape[0], self.embedding_dim - matrix.shape[1]), dtype=np.float32)
            matrix = np.hstack([matrix, padding])
        else:
            matrix = matrix[:, :self.embedding_dim]
        return matrix

    def build_index(self, df: pd.DataFrame) -> None:
        """Build FAISS index from DataFrame with clean_text column."""
        texts = df["clean_text"].fillna("").tolist()
        self.report_ids = df["report_id"].tolist()
        self.df_metadata = df.copy()
        self._corpus_texts = texts  # Store for TF-IDF fitting

        print(f"[Similarity] Encoding {len(texts)} reports...")
        self.embeddings = self.encode(texts).astype(np.float32)

        # Normalize for cosine similarity
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        self.embeddings_normalized = self.embeddings / norms

        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product = cosine after normalize
            self.index.add(self.embeddings_normalized)
            print(f"[Similarity] FAISS index built with {self.index.ntotal} vectors")
        else:
            print("[Similarity] FAISS not available — using numpy cosine similarity")

        # Save embeddings
        EMBEDDINGS_PATH.mkdir(parents=True, exist_ok=True)
        np.save(EMBEDDINGS_PATH / "embeddings.npy", self.embeddings)
        df[["report_id"]].to_csv(EMBEDDINGS_PATH / "report_ids.csv", index=False)
        print(f"[Similarity] Embeddings saved to {EMBEDDINGS_PATH}")

    def find_similar(
        self,
        query_text: str,
        exclude_id: Optional[str] = None,
        top_k: int = TOP_K_SIMILAR,
    ) -> List[Dict]:
        """Return top-k similar incidents for a query text."""
        if self.embeddings is None:
            return []

        q_vec = self.encode([query_text]).astype(np.float32)
        q_norm = q_vec / (np.linalg.norm(q_vec) + 1e-9)

        if FAISS_AVAILABLE and self.index is not None:
            scores, indices = self.index.search(q_norm, top_k + 5)
            scores = scores[0]
            indices = indices[0]
        else:
            # numpy fallback
            sims = self.embeddings_normalized @ q_norm.T
            sims = sims.flatten()
            indices = np.argsort(-sims)[: top_k + 5]
            scores = sims[indices]

        results = []
        for score, idx in zip(scores, indices):
            if idx < 0 or idx >= len(self.report_ids):
                continue
            rid = self.report_ids[idx]
            if exclude_id and rid == exclude_id:
                continue
            if float(score) < SIMILARITY_THRESHOLD:
                continue

            meta = {}
            if self.df_metadata is not None:
                row = self.df_metadata[self.df_metadata["report_id"] == rid]
                if len(row):
                    r = row.iloc[0]
                    meta = {
                        "source": r.get("source", ""),
                        "date": r.get("report_date", ""),
                        "site": r.get("site", ""),
                        "activity": r.get("activity", ""),
                        "actual_severity": r.get("actual_severity", ""),
                        "sif_label": r.get("sif_label", ""),
                        "sif_risk_score": r.get("sif_risk_score", ""),
                        "hazards": r.get("hazards", ""),
                        "life_saving_rules": r.get("life_saving_rules", ""),
                        "snippet": str(r.get("clean_text", ""))[:180] + "...",
                    }

            results.append({
                "report_id": rid,
                "similarity_score": round(float(score), 3),
                **meta,
            })
            if len(results) >= top_k:
                break

        return results

    def find_similar_by_id(self, report_id: str, top_k: int = TOP_K_SIMILAR) -> List[Dict]:
        """Find similar reports to an existing report by ID."""
        if self.df_metadata is None:
            return []
        row = self.df_metadata[self.df_metadata["report_id"] == report_id]
        if not len(row):
            return []
        text = row.iloc[0]["clean_text"]
        return self.find_similar(text, exclude_id=report_id, top_k=top_k)


# ─── Pattern Detection ────────────────────────────────────────────────────────

class PatternDetector:
    """
    Phase 9: Detect recurring SIF precursor combinations.
    Uses categorical aggregation + frequency analysis.
    """

    def detect_patterns(self, df: pd.DataFrame, min_support: int = 2) -> pd.DataFrame:
        """
        Find (Activity, Hazard, Barrier_Failure, Site) combos above min_support.
        Returns a DataFrame of patterns with IDs and metrics.
        """
        records = []

        for _, row in df.iterrows():
            hazards = self._parse_list_field(row, "hazards")
            failures = self._parse_list_field(row, "barrier_failures")
            activity = str(row.get("activity", "Unknown")).strip() or "Unknown"
            site = str(row.get("site", "Unknown")).strip() or "Unknown"
            sif_score = float(row.get("sif_risk_score", 0) or 0)

            for h in hazards[:2]:  # top 2 hazards per report
                for f in (failures[:2] if failures else ["No Barrier Failure"]):
                    records.append({
                        "report_id": row["report_id"],
                        "activity": activity,
                        "hazard": h,
                        "barrier_failure": f,
                        "site": site,
                        "sif_risk_score": sif_score,
                        "is_sif": row.get("sif_label", "") in (
                            "High-Confidence SIF", "Potential SIF"
                        ),
                    })

        if not records:
            return pd.DataFrame()

        combo_df = pd.DataFrame(records)

        # Group by (activity, hazard, barrier_failure)
        grouped = (
            combo_df.groupby(["activity", "hazard", "barrier_failure"])
            .agg(
                report_count=("report_id", "nunique"),
                avg_sif_score=("sif_risk_score", "mean"),
                sif_count=("is_sif", "sum"),
                top_sites=("site", lambda x: ", ".join(x.value_counts().head(3).index.tolist())),
                report_ids=("report_id", lambda x: list(x.unique())[:10]),
            )
            .reset_index()
        )

        # Filter by min support
        grouped = grouped[grouped["report_count"] >= min_support].copy()

        if len(grouped) == 0:
            return pd.DataFrame()

        grouped["sif_density_pct"] = (
            grouped["sif_count"] / grouped["report_count"] * 100
        ).round(1)
        grouped["avg_sif_score"] = grouped["avg_sif_score"].round(1)

        # Assign pattern IDs
        grouped = grouped.sort_values("avg_sif_score", ascending=False).reset_index(drop=True)
        grouped["pattern_id"] = [f"P-{str(i+1).zfill(3)}" for i in range(len(grouped))]

        return grouped

    def _parse_list_field(self, row: pd.Series, field: str) -> List[str]:
        val = row.get(field, "")
        if isinstance(val, list):
            return [str(v) for v in val]
        if isinstance(val, str) and val.startswith("["):
            try:
                return json.loads(val.replace("'", '"'))
            except Exception:
                pass
        if isinstance(val, str) and val:
            return [v.strip() for v in val.split(",") if v.strip()]
        return ["Unknown"]


if __name__ == "__main__":
    # Quick test
    engine = SimilarityEngine()
    engine.load_model()
    print("Similarity engine initialized.")

    detector = PatternDetector()
    print("Pattern detector initialized.")
