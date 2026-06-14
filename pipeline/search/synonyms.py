"""Configurable search synonym groups — SQLite-backed with AI/ML defaults."""

import json
import os
import sqlite3
import uuid
from datetime import datetime


class SynonymManager:
    def __init__(self, db_path: str = "./data/synonyms.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS synonym_groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS synonym_terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT NOT NULL,
                    term TEXT NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES synonym_groups(id) ON DELETE CASCADE,
                    UNIQUE(group_id, term)
                );
                CREATE INDEX IF NOT EXISTS idx_synonym_terms_term ON synonym_terms(term);
                CREATE INDEX IF NOT EXISTS idx_synonym_terms_group ON synonym_terms(group_id);
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def add_synonym_group(self, name: str, terms: list[str]) -> str:
        group_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO synonym_groups (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (group_id, name, now, now)
                )
                for term in set(t.lower().strip() for t in terms if t.strip()):
                    conn.execute(
                        "INSERT OR IGNORE INTO synonym_terms (group_id, term) VALUES (?, ?)",
                        (group_id, term)
                    )
                return group_id
            except sqlite3.IntegrityError:
                existing = conn.execute(
                    "SELECT id FROM synonym_groups WHERE name = ?", (name,)
                ).fetchone()
                if existing:
                    return existing[0]
                raise

    def remove_synonym_group(self, group_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM synonym_terms WHERE group_id = ?", (group_id,))
            conn.execute("DELETE FROM synonym_groups WHERE id = ?", (group_id,))
            return conn.rowcount > 0

    def add_term(self, group_id: str, term: str) -> bool:
        term = term.lower().strip()
        if not term:
            return False
        with self._conn() as conn:
            group = conn.execute(
                "SELECT id FROM synonym_groups WHERE id = ?", (group_id,)
            ).fetchone()
            if not group:
                return False
            conn.execute(
                "INSERT OR IGNORE INTO synonym_terms (group_id, term) VALUES (?, ?)",
                (group_id, term)
            )
            conn.execute(
                "UPDATE synonym_groups SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), group_id)
            )
            return True

    def remove_term(self, group_id: str, term: str) -> bool:
        term = term.lower().strip()
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM synonym_terms WHERE group_id = ? AND term = ?",
                (group_id, term)
            )
            return conn.rowcount > 0

    def get_synonyms(self, term: str) -> list[str]:
        term = term.lower().strip()
        with self._conn() as conn:
            row = conn.execute("""
                SELECT st.group_id FROM synonym_terms st
                WHERE st.term = ?
                LIMIT 1
            """, (term,)).fetchone()
            if not row:
                return []
            rows = conn.execute(
                "SELECT term FROM synonym_terms WHERE group_id = ? AND term != ?",
                (row[0], term)
            ).fetchall()
            return [r[0] for r in rows]

    def expand_query(self, query: str) -> str:
        words = query.lower().split()
        expanded_parts = []
        for word in words:
            word_clean = word.strip("""'\".,!?;:()[]{}""")
            synonyms = self.get_synonyms(word_clean)
            if synonyms:
                all_terms = [word_clean] + synonyms
                expanded_parts.append(f"({' OR '.join(all_terms)})")
            else:
                expanded_parts.append(word)
        return " ".join(expanded_parts)

    def list_groups(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT g.id, g.name, g.created_at, g.updated_at,
                       COUNT(st.id) as term_count
                FROM synonym_groups g
                LEFT JOIN synonym_terms st ON st.group_id = g.id
                GROUP BY g.id
                ORDER BY g.name ASC
            """).fetchall()
            result = []
            for r in rows:
                terms = conn.execute(
                    "SELECT term FROM synonym_terms WHERE group_id = ? ORDER BY term",
                    (r[0],)
                ).fetchall()
                result.append({
                    "id": r[0],
                    "name": r[1],
                    "created_at": r[2],
                    "updated_at": r[3],
                    "term_count": r[4],
                    "terms": [t[0] for t in terms],
                })
            return result

    def import_defaults(self) -> int:
        defaults = {
            "AI": ["ai", "artificial intelligence", "machine learning", "deep learning", "neural network"],
            "Agent": ["agent", "multi-agent", "agentic", "autonomous", "assistant"],
            "LLM": ["llm", "large language model", "gpt", "language model", "foundation model"],
            "RAG": ["rag", "retrieval augmented", "retrieval", "vector search"],
            "Robot": ["robot", "robotics", "robotic", "humanoid", "automaton"],
            "Quantum": ["quantum", "quantum computing", "qubit", "qbit"],
        }
        count = 0
        for name, terms in defaults.items():
            try:
                self.add_synonym_group(name, terms)
                count += len(terms)
            except Exception:
                existing = None
                with self._conn() as conn:
                    row = conn.execute(
                        "SELECT id FROM synonym_groups WHERE name = ?", (name,)
                    ).fetchone()
                    if row:
                        existing = row[0]
                if existing:
                    for t in terms:
                        self.add_term(existing, t)
                        count += 1
        return count

    def export_synonyms(self, format: str = "json") -> str:
        groups = self.list_groups()
        if format == "json":
            return json.dumps(groups, indent=2, default=str)
        elif format == "csv":
            lines = ["group_id,name,term"]
            for g in groups:
                for t in g["terms"]:
                    lines.append(f"{g['id']},{g['name']},{t}")
            return "\n".join(lines)
        return json.dumps(groups, indent=2, default=str)

    def import_synonyms(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        count = 0
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    name = item.get("name", item.get("group_name", ""))
                    terms = item.get("terms", item.get("synonyms", []))
                    if name and terms:
                        try:
                            self.add_synonym_group(name, terms)
                            count += len(terms)
                        except Exception:
                            pass
            elif isinstance(data, dict):
                for name, terms in data.items():
                    if isinstance(terms, list) and terms:
                        try:
                            self.add_synonym_group(name, terms)
                            count += len(terms)
                        except Exception:
                            pass
        except json.JSONDecodeError:
            lines = content.split("\n")
            current_name = None
            current_terms = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("//"):
                    continue
                parts = line.split(",")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    terms = [t.strip() for t in parts[1:] if t.strip()]
                    if name and terms:
                        try:
                            self.add_synonym_group(name, terms)
                            count += len(terms)
                        except Exception:
                            pass
        return count

    def get_stats(self) -> dict:
        with self._conn() as conn:
            total_groups = conn.execute("SELECT COUNT(*) FROM synonym_groups").fetchone()[0]
            total_terms = conn.execute("SELECT COUNT(*) FROM synonym_terms").fetchone()[0]
            largest = conn.execute("""
                SELECT g.name, COUNT(st.id) as cnt
                FROM synonym_groups g
                JOIN synonym_terms st ON st.group_id = g.id
                GROUP BY g.id
                ORDER BY cnt DESC
                LIMIT 1
            """).fetchone()
        return {
            "total_groups": total_groups,
            "total_terms": total_terms,
            "largest_group": {"name": largest[0], "term_count": largest[1]} if largest else None,
        }
