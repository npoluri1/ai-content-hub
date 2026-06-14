import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class GDPRCompliance:
    def __init__(self, sql_store=None, vector_store=None, data_dir: str = "./data/gdpr"):
        self.sql_store = sql_store
        self.vector_store = vector_store
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "gdpr.db")
        os.makedirs(data_dir, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS dsar_requests (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'submitted',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    details TEXT
                );
                CREATE TABLE IF NOT EXISTS consent_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    action TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE(user_email, action, purpose)
                );
                CREATE TABLE IF NOT EXISTS erasure_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    sql_deleted INTEGER DEFAULT 0,
                    vector_deleted INTEGER DEFAULT 0
                );
            """)

    def _find_user_data_in_sql(self, user_email: str) -> list[dict]:
        results = []
        if not self.sql_store:
            return results
        try:
            with self.sql_store._get_conn() as conn:
                conn.row_factory = sqlite3.Row
                tables = ["linkedin_posts", "reddit_posts", "news_articles", "processed_items"]
                for table in tables:
                    try:
                        rows = conn.execute(
                            f"SELECT * FROM {table} WHERE author_name = ? OR author_url LIKE ?",
                            (user_email, f"%{user_email}%")
                        ).fetchall()
                        for r in rows:
                            results.append({"source": "sql", "table": table, "data": dict(r)})
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"Error searching sql_store: {e}")
        return results

    def _find_user_data_in_vector(self, user_email: str) -> list[dict]:
        results = []
        if not self.vector_store:
            return results
        try:
            ids = self.vector_store.list_ids()
            for vid in ids:
                meta = getattr(self.vector_store, "get_metadata", lambda x: {})(vid)
                if isinstance(meta, dict):
                    for val in meta.values():
                        if isinstance(val, str) and user_email in val:
                            results.append({"source": "vector", "id": vid, "metadata": meta})
                            break
        except Exception as e:
            logger.warning(f"Error searching vector_store: {e}")
        return results

    def handle_dsar_request(self, user_email: str, request_id: str = None) -> dict:
        if not request_id:
            request_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        sql_items = self._find_user_data_in_sql(user_email)
        vec_items = self._find_user_data_in_vector(user_email)

        sources = set()
        storage_locations = set()
        for item in sql_items:
            sources.add(item["source"])
            storage_locations.add(f"sql:{item['table']}")
        for item in vec_items:
            sources.add(item["source"])
            storage_locations.add("vector_store")

        all_items = sql_items + vec_items
        result = {
            "request_id": request_id,
            "user": user_email,
            "items_found": [{"source": i["source"], "id": i.get("id") or i.get("data", {}).get("id")} for i in all_items],
            "sources": sorted(sources),
            "storage_locations": sorted(storage_locations),
            "created_at": now,
        }

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO dsar_requests (id, user_email, status, created_at, details) VALUES (?, ?, ?, ?, ?)",
                (request_id, user_email, "completed", now, json.dumps(result)),
            )

        logger.info(f"DSAR request {request_id} for {user_email}: {len(all_items)} items found")
        return result

    def right_to_erasure(self, user_email: str, confirm: bool = False) -> dict:
        if not confirm:
            return {"deleted_from_sql": 0, "deleted_from_vector": 0, "status": "confirmation_required"}

        now = datetime.utcnow().isoformat()
        sql_deleted = 0
        vector_deleted = 0

        if self.sql_store:
            tables = ["linkedin_posts", "reddit_posts", "news_articles", "processed_items"]
            try:
                with self.sql_store._get_conn() as conn:
                    for table in tables:
                        try:
                            cur = conn.execute(
                                f"DELETE FROM {table} WHERE author_name = ? OR author_url LIKE ?",
                                (user_email, f"%{user_email}%")
                            )
                            sql_deleted += cur.rowcount
                        except Exception:
                            continue
                    conn.commit()
            except Exception as e:
                logger.warning(f"SQL erasure error: {e}")

        if self.vector_store:
            try:
                ids = self.vector_store.list_ids()
                to_delete = []
                for vid in ids:
                    meta = getattr(self.vector_store, "get_metadata", lambda x: {})(vid)
                    if isinstance(meta, dict):
                        for val in meta.values():
                            if isinstance(val, str) and user_email in val:
                                to_delete.append(vid)
                                break
                for vid in to_delete:
                    self.vector_store.delete(vid)
                vector_deleted = len(to_delete)
            except Exception as e:
                logger.warning(f"Vector erasure error: {e}")

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO erasure_requests (user_email, executed_at, sql_deleted, vector_deleted) VALUES (?, ?, ?, ?)",
                (user_email, now, sql_deleted, vector_deleted),
            )

        logger.info(f"Right to erasure executed for {user_email}: SQL={sql_deleted}, Vector={vector_deleted}")
        return {
            "deleted_from_sql": sql_deleted,
            "deleted_from_vector": vector_deleted,
            "status": "completed",
        }

    def right_to_rectification(self, user_email: str, corrections: dict) -> dict:
        updated_fields = []
        if not self.sql_store:
            return {"updated_fields": [], "status": "no_sql_store"}

        tables = ["linkedin_posts", "reddit_posts", "news_articles", "processed_items"]
        try:
            with self.sql_store._get_conn() as conn:
                for table in tables:
                    for field, new_value in corrections.items():
                        if field in ("author_name", "author_url", "content", "title"):
                            try:
                                cur = conn.execute(
                                    f"UPDATE {table} SET {field} = ? WHERE author_name = ? OR author_url LIKE ?",
                                    (new_value, user_email, f"%{user_email}%")
                                )
                                if cur.rowcount > 0:
                                    updated_fields.append({"table": table, "field": field, "count": cur.rowcount})
                            except Exception:
                                continue
                conn.commit()
        except Exception as e:
            logger.warning(f"Rectification error: {e}")

        return {"updated_fields": updated_fields, "status": "completed"}

    def data_portability(self, user_email: str, format: str = "json") -> str:
        sql_items = self._find_user_data_in_sql(user_email)
        vec_items = self._find_user_data_in_vector(user_email)
        export = {
            "exported_at": datetime.utcnow().isoformat(),
            "user": user_email,
            "data": {
                "sql_records": [i["data"] for i in sql_items],
                "vector_records": [i["metadata"] for i in vec_items],
            },
        }
        if format == "json":
            return json.dumps(export, indent=2, default=str)
        return json.dumps(export, indent=2, default=str)

    def consent_record(self, user_email: str, action: str, purpose: str = "content_processing") -> bool:
        now = datetime.utcnow().isoformat()
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO consent_records (user_email, action, purpose, recorded_at) VALUES (?, ?, ?, ?)",
                    (user_email, action, purpose, now),
                )
            logger.info(f"Consent recorded: {user_email} {action} for {purpose}")
            return True
        except Exception as e:
            logger.error(f"Consent record failed: {e}")
            return False

    def get_consent_history(self, user_email: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM consent_records WHERE user_email = ? ORDER BY recorded_at DESC", (user_email,)
            ).fetchall()
        return [dict(r) for r in rows]

    def privacy_impact_assessment(self, data_processed: dict) -> dict:
        risk_score = 0.0
        data_categories = []

        for category in data_processed.get("data_categories", []):
            data_categories.append(category)
            if category in ("biometric", "health", "genetic", "criminal_convictions"):
                risk_score += 0.35
            elif category in ("financial", "location", "political_opinion", "religious_beliefs"):
                risk_score += 0.25
            elif category in ("contact", "name", "email", "phone"):
                risk_score += 0.10
            else:
                risk_score += 0.05

        processing_scale = data_processed.get("processing_scale", "small")
        if processing_scale == "large":
            risk_score += 0.20
        elif processing_scale == "medium":
            risk_score += 0.10

        new_technology = data_processed.get("new_technology", False)
        if new_technology:
            risk_score += 0.15

        cross_border = data_processed.get("cross_border_transfer", False)
        if cross_border:
            risk_score += 0.15

        risk_score = min(risk_score, 1.0)

        if risk_score >= 0.7:
            risk_level = "high"
            recommendations = [
                "Full DPIA required before processing",
                "Consult with DPO immediately",
                "Implement pseudonymization measures",
                "Obtain explicit consent from data subjects",
            ]
        elif risk_score >= 0.4:
            risk_level = "medium"
            recommendations = [
                "DPIA recommended",
                "Review data minimization practices",
                "Ensure lawful basis for processing is documented",
                "Implement access controls and auditing",
            ]
        else:
            risk_level = "low"
            recommendations = [
                "Standard privacy controls sufficient",
                "Document processing activities in ROPA",
                "Review privacy notice for transparency",
            ]

        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 2),
            "data_categories": data_categories,
            "retention_period": data_processed.get("retention_days", 90),
            "recommendations": recommendations,
            "requires_dpia": risk_level in ("high", "medium"),
        }

    def generate_privacy_report(self) -> str:
        with self._get_conn() as conn:
            total_dsars = conn.execute("SELECT COUNT(*) FROM dsar_requests").fetchone()[0]
            open_dsars = conn.execute("SELECT COUNT(*) FROM dsar_requests WHERE status != 'completed'").fetchone()[0]
            total_consent = conn.execute("SELECT COUNT(*) FROM consent_records").fetchone()[0]
            total_erasure = conn.execute("SELECT COUNT(*) FROM erasure_requests").fetchone()[0]

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_dsar_requests": total_dsars,
                "open_dsar_requests": open_dsars,
                "total_consent_records": total_consent,
                "total_erasure_requests": total_erasure,
            },
            "status": "compliant" if open_dsars == 0 else "action_required",
        }
        return json.dumps(report, indent=2, default=str)
