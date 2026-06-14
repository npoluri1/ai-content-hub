import uuid
import json
import copy
import time
import sqlite3
import threading
from datetime import datetime
from typing import Any


class WorkflowDebugger:
    def __init__(self, engine: 'WorkflowEngine' = None):
        self._engine = engine
        self._sessions: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._db_path = "./data/debugger_sessions.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debug_sessions (
                session_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                breakpoints TEXT,
                node_history TEXT,
                current_node_id TEXT,
                context_snapshot TEXT,
                variables TEXT,
                errors TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _persist_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if not session:
            return
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT OR REPLACE INTO debug_sessions
               (session_id, workflow_id, status, created_at, updated_at, breakpoints,
                node_history, current_node_id, context_snapshot, variables, errors)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                session.get("workflow", {}).get("id", ""),
                session.get("status", ""),
                session.get("created_at", ""),
                datetime.utcnow().isoformat(),
                json.dumps(list(session.get("breakpoints", set()))),
                json.dumps(session.get("node_history", []), default=str),
                session.get("current_node_id", ""),
                json.dumps(session.get("context", {}), default=str),
                json.dumps(session.get("variables", {}), default=str),
                json.dumps(session.get("errors", []), default=str),
            ),
        )
        conn.commit()
        conn.close()

    def start_debug_session(self, workflow: dict, breakpoints: list[str] = None) -> str:
        session_id = f"dbg_{uuid.uuid4().hex[:12]}"
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])
        start_node_id = self._find_start_node(nodes, edges)

        session = {
            "session_id": session_id,
            "workflow": copy.deepcopy(workflow),
            "workflow_id": workflow.get("id", "unknown"),
            "status": "running",
            "breakpoints": set(breakpoints or []),
            "node_history": [],
            "current_node_id": start_node_id,
            "context": {
                "workflow_id": workflow.get("id", ""),
                "workflow_name": workflow.get("name", ""),
                "started_at": datetime.utcnow().isoformat(),
                "_node_history": [],
                "_debug_session_id": session_id,
            },
            "variables": {},
            "errors": [],
            "created_at": datetime.utcnow().isoformat(),
            "trace": [],
            "paused_at_node_ids": [],
            "execution_plan": self._build_execution_plan(nodes, edges, start_node_id),
        }

        with self._lock:
            self._sessions[session_id] = session
        self._persist_session(session_id)
        return session_id

    def _find_start_node(self, nodes: list[dict], edges: list[dict]) -> str:
        target_ids = {e.get("to") for e in edges}
        for node in nodes:
            nid = node.get("id", "")
            if nid and nid not in target_ids:
                return nid
        return nodes[0].get("id", "") if nodes else ""

    def _build_execution_plan(self, nodes: list[dict], edges: list[dict], start_id: str) -> list[str]:
        adj = {}
        for edge in edges:
            from_id = edge.get("from", "")
            to_id = edge.get("to", "")
            if from_id not in adj:
                adj[from_id] = []
            adj[from_id].append(to_id)

        plan = []
        visited = set()

        def dfs(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            plan.append(node_id)
            for neighbor in adj.get(node_id, []):
                dfs(neighbor)

        dfs(start_id)
        return plan

    def step_over(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")
            if session["status"] != "running":
                return {"error": "Session is not running", "session_id": session_id}

            current_id = session["current_node_id"]
            if not current_id or current_id not in session.get("execution_plan", []):
                return {
                    "session_id": session_id,
                    "status": "completed",
                    "message": "Workflow execution completed",
                }

            nodes_map = {n.get("id"): n for n in session["workflow"].get("nodes", [])}
            node = nodes_map.get(current_id, {})

            start_time = time.time()
            try:
                handler = node.get("handler")
                if handler:
                    result = handler(session["context"])
                elif self._engine:
                    result = self._engine.execute_node(node, session["context"])
                else:
                    result = {"_executed": True}

                session["context"][current_id] = result

                trace_entry = {
                    "node_id": current_id,
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "duration": round(time.time() - start_time, 3),
                    "input_size": len(str(session["context"].get(current_id, ""))),
                    "output_size": len(str(result)),
                    "status": "completed",
                }
                session["trace"].append(trace_entry)
                session["node_history"].append({
                    "node_id": current_id,
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                session["context"]["_node_history"] = session["node_history"]

            except Exception as e:
                trace_entry = {
                    "node_id": current_id,
                    "start_time": datetime.utcnow().isoformat(),
                    "end_time": datetime.utcnow().isoformat(),
                    "duration": round(time.time() - start_time, 3),
                    "status": "failed",
                    "error": str(e),
                }
                session["trace"].append(trace_entry)
                session["node_history"].append({
                    "node_id": current_id,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                session["errors"].append({"node_id": current_id, "error": str(e)})
                result = {"_error": str(e)}

            plan = session["execution_plan"]
            current_idx = plan.index(current_id) if current_id in plan else -1
            next_id = plan[current_idx + 1] if 0 <= current_idx < len(plan) - 1 else None
            session["current_node_id"] = next_id

            if next_id is None:
                session["status"] = "completed"

            self._persist_session(session_id)

            return {
                "session_id": session_id,
                "previous_node": current_id,
                "current_node": next_id,
                "status": session["status"],
                "result": result,
                "available_actions": self._get_available_actions(session),
            }

    def step_into(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")

            current_id = session["current_node_id"]
            nodes_map = {n.get("id"): n for n in session["workflow"].get("nodes", [])}
            node = nodes_map.get(current_id, {})

            sub_workflow = node.get("sub_workflow") or node.get("transform_type")
            if sub_workflow:
                sub_context = {
                    "step_into": True,
                    "parent_session_id": session_id,
                    "parent_node_id": current_id,
                    "input_data": session["context"].get(current_id, {}),
                }
                session["context"]["_sub_context"] = sub_context
                session["status"] = "in_subworkflow"

                result = {
                    "session_id": session_id,
                    "action": "step_into",
                    "node_id": current_id,
                    "sub_workflow": sub_workflow,
                    "message": f"Stepped into sub-workflow/transform: {sub_workflow}",
                }
            else:
                result = self.step_over(session_id)

            self._persist_session(session_id)
            return result

    def step_out(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")

            sub_context = session["context"].get("_sub_context", {})
            parent_session_id = sub_context.get("parent_session_id")
            parent_node_id = sub_context.get("parent_node_id")

            if parent_session_id and parent_node_id:
                remaining = session["execution_plan"][session["execution_plan"].index(session["current_node_id"]):]
                for node_id in remaining:
                    nodes_map = {n.get("id"): n for n in session["workflow"].get("nodes", [])}
                    node = nodes_map.get(node_id, {})
                    handler = node.get("handler")
                    if handler:
                        try:
                            result = handler(session["context"])
                            session["context"][node_id] = result
                        except Exception as e:
                            session["errors"].append({"node_id": node_id, "error": str(e)})
                    session["node_history"].append({
                        "node_id": node_id,
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                session["status"] = "completed"

                parent_session = self._sessions.get(parent_session_id)
                if parent_session:
                    parent_session["context"].pop("_sub_context", None)
                    if parent_node_id:
                        parent_session["context"][parent_node_id] = session["context"].get("output_result", {})

            self._persist_session(session_id)
            return {
                "session_id": session_id,
                "action": "step_out",
                "status": session["status"],
                "message": "Stepped out of sub-workflow",
            }

    def continue_execution(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")

            while session["status"] == "running" and session["current_node_id"]:
                current_id = session["current_node_id"]
                if current_id in session.get("breakpoints", set()):
                    session["paused_at_node_ids"].append(current_id)
                    self._persist_session(session_id)
                    return {
                        "session_id": session_id,
                        "status": "paused",
                        "paused_at": current_id,
                        "message": f"Paused at breakpoint: {current_id}",
                    }

                step_result = self.step_over(session_id)
                if step_result.get("status") == "completed":
                    self._persist_session(session_id)
                    return step_result

                if step_result.get("status") != "running":
                    self._persist_session(session_id)
                    return step_result

            self._persist_session(session_id)
            return {
                "session_id": session_id,
                "status": session["status"],
                "message": "Workflow execution completed",
            }

    def set_breakpoint(self, session_id: str, node_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session["breakpoints"].add(node_id)
            self._persist_session(session_id)
            return True

    def remove_breakpoint(self, session_id: str, node_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session["breakpoints"].discard(node_id)
            self._persist_session(session_id)
            return True

    def get_state(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")
            return {
                "session_id": session_id,
                "workflow_id": session.get("workflow_id"),
                "current_node": session.get("current_node_id"),
                "status": session.get("status"),
                "node_history": session.get("node_history", []),
                "context_size": len(str(session.get("context", {}))),
                "variables": list(session.get("variables", {}).keys()),
                "errors": session.get("errors", []),
                "breakpoints": list(session.get("breakpoints", set())),
                "trace_count": len(session.get("trace", [])),
            }

    def inspect_variable(self, session_id: str, var_path: str) -> Any:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")
            parts = var_path.split(".")
            value = session.get("context", {})
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, {})
                else:
                    return None
            return value if value != {} else None

    def modify_state(self, session_id: str, var_path: str, value: Any) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            parts = var_path.split(".")
            target = session.get("context", {})
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value
            self._persist_session(session_id)
            return True

    def get_execution_trace(self, session_id: str) -> list[dict]:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session '{session_id}' not found")
            return list(session.get("trace", []))

    def end_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            session["status"] = "ended"
            self._persist_session(session_id)
            return True

    def list_sessions(self, status: str = None, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(self._db_path)
        if status:
            rows = conn.execute(
                "SELECT session_id, workflow_id, status, created_at, updated_at FROM debug_sessions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT session_id, workflow_id, status, created_at, updated_at FROM debug_sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _get_available_actions(self, session: dict) -> list[str]:
        actions = ["step_over", "continue"]
        current_id = session.get("current_node_id")
        if current_id:
            nodes_map = {n.get("id"): n for n in session["workflow"].get("nodes", [])}
            node = nodes_map.get(current_id, {})
            if node.get("sub_workflow") or node.get("transform_type"):
                actions.append("step_into")
        if session.get("context", {}).get("_sub_context"):
            actions.append("step_out")
        if session.get("breakpoints"):
            actions.append("set_breakpoint")
            actions.append("remove_breakpoint")
        return actions
