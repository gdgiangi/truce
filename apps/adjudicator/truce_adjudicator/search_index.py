"""SQLite FTS index helpers for claim and evidence search."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, List, Tuple

DB_PATH = Path(__file__).resolve().parent / "data" / "search_index.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_CONNECTION = sqlite3.connect(DB_PATH, check_same_thread=False)
_CONNECTION.row_factory = sqlite3.Row
_LOCK = Lock()


def _initialize() -> None:
    """Create required FTS5 tables if they do not exist."""
    with _LOCK:
        _CONNECTION.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS claim_search USING fts5(slug UNINDEXED, text)"
        )
        _CONNECTION.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS evidence_search USING fts5("
            "claim_slug UNINDEXED, evidence_id UNINDEXED, snippet, publisher, url)"
        )
        _CONNECTION.commit()


_initialize()


def reset() -> None:
    """Remove all index entries. Used mainly for tests."""
    with _LOCK:
        _CONNECTION.execute("DELETE FROM claim_search")
        _CONNECTION.execute("DELETE FROM evidence_search")
        _CONNECTION.commit()


def index_claim(slug: str, text: str) -> None:
    """Insert or update a claim entry in the FTS index."""
    normalized = text.strip()
    with _LOCK:
        _CONNECTION.execute("DELETE FROM claim_search WHERE slug = ?", (slug,))
        _CONNECTION.execute(
            "INSERT INTO claim_search(slug, text) VALUES (?, ?)",
            (slug, normalized),
        )
        _CONNECTION.commit()


def remove_claim(slug: str) -> None:
    """Remove claim and its evidence entries from the index."""
    with _LOCK:
        _CONNECTION.execute("DELETE FROM claim_search WHERE slug = ?", (slug,))
        _CONNECTION.execute("DELETE FROM evidence_search WHERE claim_slug = ?", (slug,))
        _CONNECTION.commit()


def index_evidence(
    claim_slug: str,
    evidence_id: str,
    snippet: str,
    publisher: str,
    url: str,
) -> None:
    """Insert or update evidence-related search entry."""
    with _LOCK:
        _CONNECTION.execute(
            "DELETE FROM evidence_search WHERE evidence_id = ?", (evidence_id,)
        )
        _CONNECTION.execute(
            "INSERT INTO evidence_search(claim_slug, evidence_id, snippet, publisher, url) "
            "VALUES (?, ?, ?, ?, ?)",
            (claim_slug, evidence_id, snippet.strip(), publisher.strip(), url.strip()),
        )
        _CONNECTION.commit()


def index_evidence_batch(
    claim_slug: str,
    items: Iterable[Dict[str, str]],
) -> None:
    """Bulk insert evidence entries to reduce transaction overhead."""
    with _LOCK:
        for item in items:
            evidence_id = item.get("evidence_id")
            snippet = item.get("snippet", "")
            publisher = item.get("publisher", "")
            url = item.get("url", "")
            if not evidence_id:
                continue
            _CONNECTION.execute(
                "DELETE FROM evidence_search WHERE evidence_id = ?",
                (evidence_id,),
            )
            _CONNECTION.execute(
                "INSERT INTO evidence_search(claim_slug, evidence_id, snippet, publisher, url) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    claim_slug,
                    evidence_id,
                    snippet.strip(),
                    publisher.strip(),
                    url.strip(),
                ),
            )
        _CONNECTION.commit()


def _prepare_match_query(query: str) -> str:
    tokens = [token for token in query.strip().split() if token]
    if not tokens:
        return ""
    return " ".join(f"{token}*" for token in tokens)


def search(
    query: str, claim_limit: int = 5, evidence_limit: int = 10
) -> Tuple[List[sqlite3.Row], List[sqlite3.Row]]:
    """Run FTS query across claims and evidence tables."""
    prepared = _prepare_match_query(query)
    if not prepared:
        return [], []

    with _LOCK:
        claim_rows = _CONNECTION.execute(
            "SELECT slug, text, bm25(claim_search) AS score FROM claim_search "
            "WHERE claim_search MATCH ? ORDER BY score LIMIT ?",
            (prepared, claim_limit),
        ).fetchall()
        evidence_rows = _CONNECTION.execute(
            "SELECT claim_slug, evidence_id, snippet, publisher, url, bm25(evidence_search) AS score "
            "FROM evidence_search WHERE evidence_search MATCH ? ORDER BY score LIMIT ?",
            (prepared, evidence_limit),
        ).fetchall()

    return claim_rows, evidence_rows
