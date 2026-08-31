"""SQLite storage for paper records."""
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


class Storage:
    """Manages the SQLite database for paper records."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    categories TEXT,
                    link TEXT,
                    published TEXT,
                    category INTEGER DEFAULT 0,
                    summary_zh TEXT,
                    relevance_reason TEXT,
                    processed_at TEXT DEFAULT (datetime('now')),
                    notified INTEGER DEFAULT 0,
                    to_read INTEGER DEFAULT 0
                )
            """)

    def save_paper(self, paper: Dict[str, Any], classification: Dict[str, Any]):
        """Insert or update a paper record."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO papers (
                    arxiv_id, title, authors, abstract, categories, link,
                    published, category, summary_zh, relevance_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(arxiv_id) DO UPDATE SET
                    category = excluded.category,
                    summary_zh = excluded.summary_zh,
                    relevance_reason = excluded.relevance_reason
            """, (
                paper["arxiv_id"],
                paper["title"],
                ", ".join(paper["authors"]),
                paper["abstract"],
                ", ".join(paper["categories"]),
                paper["link"],
                paper["published"],
                classification.get("category", 1),
                classification.get("summary_zh", ""),
                classification.get("relevance_reason", ""),
            ))

    def paper_exists(self, arxiv_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("SELECT 1 FROM papers WHERE arxiv_id = ?", (arxiv_id,))
            return cur.fetchone() is not None

    def get_papers_by_category(self, category: int, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM papers WHERE category = ? ORDER BY published DESC LIMIT ?",
                (category, limit)
            )
            return [dict(r) for r in cur.fetchall()]

    def mark_notified(self, arxiv_id: str):
        with self._connect() as conn:
            conn.execute("UPDATE papers SET notified = 1 WHERE arxiv_id = ?", (arxiv_id,))

    def mark_to_read(self, arxiv_id: str):
        with self._connect() as conn:
            conn.execute("UPDATE papers SET to_read = 1 WHERE arxiv_id = ?", (arxiv_id,))

    def get_unnotified(self, category: int) -> List[Dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM papers WHERE category = ? AND notified = 0 ORDER BY published DESC",
                (category,)
            )
            return [dict(r) for r in cur.fetchall()]
