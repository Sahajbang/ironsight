"""Hybrid search over the operator knowledge layer (PRD §11).

Three signals combined per document:
  1. word-level TF-IDF  — exact/lexical relevance
  2. char n-gram TF-IDF — morphology and typo tolerance ("trench" ~ "trenching")
  3. fuzzy token match  — heavy misspellings ("proxmitiy alrt" -> "proximity alert")
plus a domain synonym expansion and a context boost for the operator's current
machine/task, so the same query ranks differently in different situations (§11.5).

ponytail: no pgvector/OpenSearch and no embedding model — the corpus is tens of documents
and rebuilds in milliseconds. Swap in a real embedding index if the corpus outgrows ~10k rows.
"""
import re
import threading

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m

SYNONYMS = {
    "dig": ["excavation", "excavate", "trenching"],
    "digging": ["excavation", "trenching"],
    "trench": ["trenching"],
    "belt": ["seatbelt"],
    "alert": ["alarm", "warning", "hazard"],
    "alarm": ["alert", "warning"],
    "proximity": ["clearance", "distance", "personnel"],
    "close": ["proximity", "clearance"],
    "load": ["loading", "bucket", "material"],
    "manual": ["handbook", "reference"],
    "book": ["handbook", "manual"],
    "grade": ["grading"],
    "safe": ["safety"],
    "safely": ["safety"],
    "how": [],
    "to": [],
    "the": [],
}

RESULT_TYPE_LABELS = {
    "video": "Video",
    "handbook": "Manual / Handbook",
    "checklist": "Checklist",
    "instructor": "Instructor",
    "simulation": "Simulation",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _expand(query: str) -> str:
    out = []
    for token in _tokens(query):
        out.append(token)
        out.extend(SYNONYMS.get(token, []))
    return " ".join(out) if out else query.lower()


class SearchIndex:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._docs: list[dict] = []
        self._doc_tokens: list[set[str]] = []
        self._title_tokens: list[set[str]] = []
        self._word_vec: TfidfVectorizer | None = None
        self._char_vec: TfidfVectorizer | None = None
        self._word_matrix = None
        self._char_matrix = None
        self._built_for = -1

    def build(self, db: Session, force: bool = False) -> None:
        rows = list(db.scalars(select(m.TrainingContent).order_by(m.TrainingContent.id)))
        with self._lock:
            if not force and self._built_for == len(rows) and self._docs:
                return
            self._docs = [
                {
                    "id": r.id,
                    "title": r.title,
                    "content_type": r.content_type,
                    "machine_family": r.machine_family,
                    "task_type": r.task_type,
                    "skill_level": r.skill_level,
                    "duration_min": r.duration_min,
                    "body_text": r.body_text,
                    "url": r.url,
                }
                for r in rows
            ]
            corpus = [
                f"{d['title']} {d['body_text']} {d['task_type'] or ''} {d['machine_family']} {d['content_type']}"
                for d in self._docs
            ]
            self._doc_tokens = [set(_tokens(text)) for text in corpus]
            self._title_tokens = [set(_tokens(d["title"])) for d in self._docs]
            if not corpus:
                self._word_vec = self._char_vec = None
                self._built_for = 0
                return
            self._word_vec = TfidfVectorizer(sublinear_tf=True, stop_words="english")
            self._word_matrix = self._word_vec.fit_transform(corpus)
            self._char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
            self._char_matrix = self._char_vec.fit_transform(corpus)
            self._built_for = len(rows)

    def _fuzzy_scores(self, query: str, token_sets: list[set[str]]) -> list[float]:
        """Per-query-token best fuzzy match against a document's tokens, averaged.

        Scoring token-by-token (rather than one ratio over the whole string) is what makes
        heavy misspellings work: "proxmitiy"~"proximity" and "alrt"~"alert" each score high
        on their own, where a whole-string comparison would be diluted by the rest of the text.
        """
        q_tokens = [t for t in _tokens(query) if len(t) > 2]
        if not q_tokens:
            return [0.0] * len(self._docs)
        scores = []
        for doc_tokens in token_sets:
            per_token = [
                max((fuzz.ratio(qt, dt) for dt in doc_tokens), default=0) / 100.0
                for qt in q_tokens
            ]
            scores.append(sum(per_token) / len(per_token))
        return scores

    def search(self, db: Session, query: str, limit: int = 12,
               machine_type: str | None = None, task_type: str | None = None,
               skill_level: str | None = None, content_type: str | None = None) -> list[dict]:
        self.build(db)
        if not self._docs or not query.strip():
            return []

        expanded = _expand(query)
        word_sim = cosine_similarity(self._word_vec.transform([expanded]), self._word_matrix)[0]
        char_sim = cosine_similarity(self._char_vec.transform([query.lower()]), self._char_matrix)[0]
        fuzzy = self._fuzzy_scores(query, self._doc_tokens)
        title_fuzzy = self._fuzzy_scores(query, self._title_tokens)

        results = []
        for i, doc in enumerate(self._docs):
            if content_type and doc["content_type"] != content_type:
                continue
            # A title hit is stronger evidence than the same words buried in body text.
            score = (0.24 * float(word_sim[i]) + 0.32 * float(char_sim[i])
                     + 0.24 * fuzzy[i] + 0.20 * title_fuzzy[i])
            reasons = []
            if task_type and doc["task_type"] == task_type:
                score += 0.12
                reasons.append(f"matches your current task ({task_type})")
            if machine_type and doc["machine_family"] in (machine_type, "All"):
                score += 0.08
                reasons.append(f"applies to your machine ({doc['machine_family']})")
            if skill_level and doc["skill_level"] in (skill_level, "All"):
                score += 0.04
            if score < 0.18:
                continue
            results.append({
                **doc,
                "result_type": RESULT_TYPE_LABELS.get(doc["content_type"], doc["content_type"].title()),
                "score": round(score, 4),
                "context_reasons": reasons,
                "snippet": doc["body_text"][:180] + ("…" if len(doc["body_text"]) > 180 else ""),
            })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]


index = SearchIndex()


def grouped_search(db: Session, query: str, **kwargs) -> dict:
    results = index.search(db, query, **kwargs)
    groups: dict[str, list[dict]] = {}
    for r in results:
        groups.setdefault(r["result_type"], []).append(r)

    quick_answer = None
    if results:
        top = results[0]
        first_sentence = top["body_text"].split(". ")[0].strip().rstrip(".")
        quick_answer = {
            "text": f"{first_sentence}.",
            "source_id": top["id"],
            "source_title": top["title"],
            "source_url": top["url"],
        }

    return {
        "query": query,
        "total": len(results),
        "quick_answer": quick_answer,
        "results": results,
        "groups": [{"type": name, "items": items} for name, items in groups.items()],
    }
