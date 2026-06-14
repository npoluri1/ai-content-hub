import sqlite3
import json
import copy
import threading
from datetime import datetime
from typing import Any


class WorkflowVersioning:
    def __init__(self, storage: 'WorkflowStorage' = None, db_path: str = "./data/workflow_versions.db"):
        self._storage = storage
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                workflow_json TEXT NOT NULL,
                created_by TEXT,
                change_notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                UNIQUE(workflow_id, version_number)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wv_workflow_id ON workflow_versions(workflow_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wv_status ON workflow_versions(status)
        """)
        conn.commit()
        conn.close()

    def save_version(self, workflow_id: str, workflow: dict, created_by: str = None, change_notes: str = None) -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(version_number) as max_ver FROM workflow_versions WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        next_version = (row["max_ver"] if row["max_ver"] else 0) + 1

        conn.execute(
            """INSERT INTO workflow_versions (workflow_id, version_number, workflow_json, created_by, change_notes, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'active', ?)""",
            (
                workflow_id,
                next_version,
                json.dumps(workflow, default=str),
                created_by,
                change_notes,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return next_version

    def get_version(self, workflow_id: str, version_number: int = None) -> dict:
        conn = self._get_conn()
        if version_number is not None:
            row = conn.execute(
                "SELECT * FROM workflow_versions WHERE workflow_id = ? AND version_number = ?",
                (workflow_id, version_number),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM workflow_versions WHERE workflow_id = ? ORDER BY version_number DESC LIMIT 1",
                (workflow_id,),
            ).fetchone()
        if not row:
            raise ValueError(f"Version {version_number or 'latest'} not found for workflow '{workflow_id}'")
        row_dict = dict(row)
        row_dict["workflow"] = json.loads(row_dict.pop("workflow_json"))
        return row_dict

    def list_versions(self, workflow_id: str) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT version_number, created_at, created_by, change_notes, status FROM workflow_versions WHERE workflow_id = ? ORDER BY version_number DESC",
            (workflow_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def rollback(self, workflow_id: str, version_number: int) -> dict:
        version_data = self.get_version(workflow_id, version_number)
        conn = self._get_conn()
        conn.execute(
            "UPDATE workflow_versions SET status = 'rollback_target' WHERE workflow_id = ? AND version_number = ?",
            (workflow_id, version_number),
        )
        next_version = version_data["version_number"] + 1
        restored_workflow = copy.deepcopy(version_data["workflow"])
        restored_workflow["_rolled_back_from"] = self._get_latest_version_number(workflow_id)
        restored_workflow["_rolled_back_to"] = version_number
        conn.execute(
            """INSERT INTO workflow_versions (workflow_id, version_number, workflow_json, created_by, change_notes, status, created_at)
               VALUES (?, ?, ?, 'system', ?, 'active', ?)""",
            (
                workflow_id,
                next_version,
                json.dumps(restored_workflow, default=str),
                f"Rollback to version {version_number}",
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return restored_workflow

    def _get_latest_version_number(self, workflow_id: str) -> int:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(version_number) as max_ver FROM workflow_versions WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()
        return row["max_ver"] if row["max_ver"] else 0

    def diff(self, workflow_id: str, version_a: int, version_b: int) -> dict:
        va = self.get_version(workflow_id, version_a)
        vb = self.get_version(workflow_id, version_b)
        wa = va["workflow"]
        wb = vb["workflow"]

        nodes_a = {n.get("id"): n for n in wa.get("nodes", [])}
        nodes_b = {n.get("id"): n for n in wb.get("nodes", [])}
        ids_a = set(nodes_a.keys())
        ids_b = set(nodes_b.keys())

        nodes_added = list(ids_b - ids_a)
        nodes_removed = list(ids_a - ids_b)
        nodes_modified = []
        for nid in ids_a & ids_b:
            if nodes_a[nid] != nodes_b[nid]:
                nodes_modified.append(nid)

        edges_a = {f"{e.get('from')}->{e.get('to')}" for e in wa.get("edges", [])}
        edges_b = {f"{e.get('from')}->{e.get('to')}" for e in wb.get("edges", [])}
        edges_added = list(edges_b - edges_a)
        edges_removed = list(edges_a - edges_b)

        return {
            "workflow_id": workflow_id,
            "version_a": version_a,
            "version_b": version_b,
            "nodes_added": [{"id": nid, "data": nodes_b.get(nid)} for nid in nodes_added],
            "nodes_removed": [{"id": nid, "data": nodes_a.get(nid)} for nid in nodes_removed],
            "nodes_modified": [{"id": nid, "old": nodes_a.get(nid), "new": nodes_b.get(nid)} for nid in nodes_modified],
            "edges_changed": {
                "added": edges_added,
                "removed": edges_removed,
            },
            "config_diff": self._dict_diff(
                {k: v for k, v in wa.items() if k not in ("nodes", "edges")},
                {k: v for k, v in wb.items() if k not in ("nodes", "edges")},
            ),
        }

    def _dict_diff(self, old: dict, new: dict) -> dict:
        diff = {}
        all_keys = set(old.keys()) | set(new.keys())
        for key in all_keys:
            if key not in old:
                diff[key] = {"old": None, "new": new[key]}
            elif key not in new:
                diff[key] = {"old": old[key], "new": None}
            elif old[key] != new[key]:
                diff[key] = {"old": old[key], "new": new[key]}
        return diff

    def compare_to_active(self, workflow_id: str, version_number: int) -> dict:
        conn = self._get_conn()
        active_row = conn.execute(
            "SELECT version_number FROM workflow_versions WHERE workflow_id = ? AND status = 'active' ORDER BY version_number DESC LIMIT 1",
            (workflow_id,),
        ).fetchone()
        if not active_row:
            raise ValueError(f"No active version found for workflow '{workflow_id}'")
        return self.diff(workflow_id, active_row["version_number"], version_number)

    def promote_version(self, workflow_id: str, version_number: int) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM workflow_versions WHERE workflow_id = ? AND version_number = ?",
            (workflow_id, version_number),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE workflow_versions SET status = 'archived' WHERE workflow_id = ? AND status = 'production'",
            (workflow_id,),
        )
        conn.execute(
            "UPDATE workflow_versions SET status = 'production' WHERE workflow_id = ? AND version_number = ?",
            (workflow_id, version_number),
        )
        conn.commit()
        return True

    def archive_version(self, workflow_id: str, version_number: int) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "UPDATE workflow_versions SET status = 'archived' WHERE workflow_id = ? AND version_number = ?",
            (workflow_id, version_number),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_version_stats(self, workflow_id: str) -> dict:
        conn = self._get_conn()
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM workflow_versions WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()["cnt"]

        latest = conn.execute(
            "SELECT MAX(version_number) as ver FROM workflow_versions WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()

        oldest = conn.execute(
            "SELECT MIN(version_number) as ver FROM workflow_versions WHERE workflow_id = ?",
            (workflow_id,),
        ).fetchone()

        last_modified_row = conn.execute(
            "SELECT created_at FROM workflow_versions WHERE workflow_id = ? ORDER BY created_at DESC LIMIT 1",
            (workflow_id,),
        ).fetchone()

        rollbacks = conn.execute(
            "SELECT COUNT(*) as cnt FROM workflow_versions WHERE workflow_id = ? AND change_notes LIKE 'Rollback%'",
            (workflow_id,),
        ).fetchone()["cnt"]

        return {
            "total_versions": total,
            "latest_version": latest["ver"] if latest else 0,
            "oldest_version": oldest["ver"] if oldest else 0,
            "last_modified": last_modified_row["created_at"] if last_modified_row else None,
            "total_rollbacks": rollbacks,
        }
