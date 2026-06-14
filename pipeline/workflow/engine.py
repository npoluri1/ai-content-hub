import threading
import uuid
import time
import json
from datetime import datetime
from collections import defaultdict
from .nodes import NodeType, WorkflowNode


class WorkflowEngine:
    def __init__(self, store=None):
        self.store = store
        self._handlers = {}
        self._executions = {}
        self._cancel_flags = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        self.register_node_handler(NodeType.TRIGGER, self._handle_trigger)
        self.register_node_handler(NodeType.COLLECT, self._handle_collect)
        self.register_node_handler(NodeType.FILTER, self._handle_filter)
        self.register_node_handler(NodeType.CLASSIFY, self._handle_classify)
        self.register_node_handler(NodeType.NOTIFY, self._handle_notify)
        self.register_node_handler(NodeType.EXPORT, self._handle_export)
        self.register_node_handler(NodeType.CONDITION, self._handle_condition)
        self.register_node_handler(NodeType.TRANSFORM, self._handle_transform)
        self.register_node_handler(NodeType.DELAY, self._handle_delay)
        self.register_node_handler(NodeType.MERGE, self._handle_merge)
        self.register_node_handler(NodeType.LOOP, self._handle_loop)
        self.register_node_handler(NodeType.END, self._handle_end)

    def register_node_handler(self, node_type, handler):
        self._handlers[node_type] = handler

    def execute(self, workflow, context=None):
        ctx = context or {}
        ctx.setdefault("node_outputs", {})
        ctx.setdefault("errors", [])
        ctx.setdefault("start_time", datetime.utcnow().isoformat())
        ctx.setdefault("results", {})
        ctx.setdefault("execution_id", str(uuid.uuid4()))
        start_wall = time.time()

        nodes = {}
        for n in workflow.get("nodes", []):
            nodes[n["id"]] = n

        incoming = defaultdict(list)
        outgoing = defaultdict(list)
        for e in workflow.get("edges", []):
            outgoing[e["from"]].append(e["to"])
            incoming[e["to"]].append(e["from"])

        start_nodes = []
        for nid, node in nodes.items():
            if node["type"] == NodeType.TRIGGER.value or not incoming.get(nid):
                start_nodes.append(nid)

        if not start_nodes:
            return {"status": "error", "errors": ["No start nodes found"], "results": {}, "execution_time": 0.0}

        visited = set()
        queue = list(start_nodes)
        node_order = []

        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node_order.append(nid)
            for out_id in outgoing.get(nid, []):
                if out_id not in visited:
                    queue.append(out_id)

        for nid in node_order:
            exec_id = ctx.get("execution_id")
            if exec_id and self._cancel_flags.get(exec_id, False):
                ctx["errors"].append({"node": nid, "error": "Execution cancelled"})
                break

            node_data = nodes.get(nid)
            if not node_data:
                continue

            wf_node = WorkflowNode(
                id=node_data["id"],
                type=NodeType(node_data["type"]),
                name=node_data.get("name", ""),
                config=node_data.get("config", {}),
                next_nodes=outgoing.get(nid, []),
            )

            try:
                next_node_id, output = self.execute_node(wf_node, ctx)
                ctx["node_outputs"][nid] = output
                ctx["results"][nid] = output

                if next_node_id:
                    route_targets = next_node_id if isinstance(next_node_id, list) else [next_node_id]
                    for rt in route_targets:
                        if rt and rt not in visited:
                            if rt not in queue:
                                idx = 0
                                if rt in node_order:
                                    pos = node_order.index(rt)
                                    for qn in list(queue):
                                        qpos = node_order.index(qn) if qn in node_order else len(node_order)
                                        if qpos > pos:
                                            break
                                        idx += 1
                                queue.insert(idx, rt)
            except Exception as e:
                ctx["errors"].append({"node": nid, "error": str(e), "node_name": wf_node.name})

        exec_time = time.time() - start_wall
        status = "completed"
        if self._cancel_flags.get(ctx.get("execution_id", ""), False):
            status = "cancelled"
        elif ctx["errors"]:
            status = "completed_with_errors"

        return {
            "status": status,
            "results": ctx["results"],
            "errors": ctx["errors"],
            "execution_time": round(exec_time, 3),
        }

    def execute_node(self, node, context):
        handler = self._handlers.get(node.type)
        if not handler:
            raise ValueError(f"No handler registered for node type: {node.type.value}")
        output = handler(node, context)
        next_node = output.get("next_node")
        return next_node, output

    def execute_async(self, workflow):
        execution_id = str(uuid.uuid4())
        self._cancel_flags[execution_id] = False

        def _run():
            context = {"execution_id": execution_id}
            result = self.execute(workflow, context)
            finished_at = datetime.utcnow().isoformat()
            self._executions[execution_id] = {
                "status": result["status"],
                "result": result,
                "started_at": context.get("start_time", finished_at),
                "finished_at": finished_at,
            }
            if self.store:
                try:
                    self.store.save_execution(execution_id, workflow.get("id", "unknown"), result["status"], result)
                except Exception:
                    pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        self._executions[execution_id] = {
            "status": "running",
            "thread": thread,
            "started_at": datetime.utcnow().isoformat(),
        }
        return execution_id

    def get_execution_status(self, execution_id):
        info = self._executions.get(execution_id)
        if not info:
            return {"status": "not_found"}
        thread = info.get("thread")
        if thread and isinstance(thread, threading.Thread) and not thread.is_alive():
            return {
                "status": info.get("status", "completed"),
                "result": info.get("result", {}),
                "started_at": info.get("started_at"),
                "finished_at": info.get("finished_at"),
            }
        return {"status": info.get("status", "running"), "started_at": info.get("started_at")}

    def cancel_execution(self, execution_id):
        if execution_id in self._cancel_flags:
            self._cancel_flags[execution_id] = True
            if execution_id in self._executions:
                self._executions[execution_id]["status"] = "cancelled"
                self._executions[execution_id]["finished_at"] = datetime.utcnow().isoformat()
            return True
        return False

    def list_executions(self, limit=20):
        results = []
        for eid, info in list(self._executions.items()):
            entry = {
                "execution_id": eid,
                "status": info.get("status", "unknown"),
                "started_at": info.get("started_at"),
                "finished_at": info.get("finished_at"),
            }
            if "result" in info and info["result"]:
                entry["execution_time"] = info["result"].get("execution_time")
                entry["error_count"] = len(info["result"].get("errors", []))
            results.append(entry)
        results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return results[:limit]

    def _handle_trigger(self, node, ctx):
        return {
            "triggered": True,
            "schedule": node.config.get("schedule"),
            "source": node.config.get("source"),
            "topic": node.config.get("topic"),
        }

    def _handle_collect(self, node, ctx):
        return {
            "items": [],
            "source": node.config.get("source"),
            "max_items": node.config.get("max_items", 10),
            "query": node.config.get("query"),
            "collected": 0,
        }

    def _handle_filter(self, node, ctx):
        prev_outputs = list(ctx.get("node_outputs", {}).values())
        items = []
        for po in prev_outputs:
            for k in ("items", "results", "data"):
                val = po.get(k, [])
                if isinstance(val, list):
                    items.extend(val)
        filtered = []
        condition = node.config.get("condition", "")
        topics = node.config.get("topics", [])
        min_rel = node.config.get("min_relevance", 0.0)
        for item in items:
            if hasattr(item, "sentiment") and abs(getattr(item, "sentiment", 0)) < min_rel:
                continue
            if hasattr(item, "topics") and topics:
                item_topics = getattr(item, "topics", [])
                if not any(t in item_topics for t in topics):
                    continue
            if condition:
                try:
                    eval_ctx = {"item": item, "ctx": ctx}
                    if not eval(condition, {"__builtins__": {}}, eval_ctx):
                        continue
                except Exception:
                    continue
            filtered.append(item)
        return {"items": filtered, "input_count": len(items), "filtered_count": len(filtered)}

    def _handle_classify(self, node, ctx):
        prev_outputs = list(ctx.get("node_outputs", {}).values())
        items = []
        for po in prev_outputs:
            for k in ("items", "results", "data"):
                val = po.get(k, [])
                if isinstance(val, list):
                    items.extend(val)
        method = node.config.get("method", "keyword")
        topics = node.config.get("topics", [])
        classified = []
        for item in items:
            if hasattr(item, "topics"):
                classified.append({"item": item, "topics": getattr(item, "topics", [])})
            else:
                classified.append({"item": item, "topics": topics})
        return {"classified": classified, "method": method, "count": len(classified)}

    def _handle_notify(self, node, ctx):
        channel = node.config.get("channel", "slack")
        template = node.config.get("message_template", "Notification from workflow")
        recipients = node.config.get("recipients", [])
        prev_outputs = list(ctx.get("node_outputs", {}).values())
        summary = {}
        for po in prev_outputs:
            summary.update(po)
        return {
            "sent": True,
            "channel": channel,
            "recipients": recipients,
            "message": template,
            "data_summary": {k: str(v)[:100] for k, v in list(summary.items())[:5]},
        }

    def _handle_export(self, node, ctx):
        fmt = node.config.get("format", "markdown")
        path = node.config.get("path", "./exports")
        include_content = node.config.get("include_content", True)
        all_data = []
        for nid, output in ctx.get("node_outputs", {}).items():
            all_data.append({"node": nid, "output": output})
        return {"exported": True, "format": fmt, "path": path, "items_exported": len(all_data)}

    def _handle_condition(self, node, ctx):
        expr = node.config.get("if_expression", "True")
        true_node = node.config.get("true_node")
        false_node = node.config.get("false_node")
        try:
            env = {"__builtins__": {}}
            env.update(ctx)
            result = bool(eval(expr, env))
        except Exception:
            result = False
        next_node = true_node if result else false_node
        return {"condition_result": result, "next_node": next_node}

    def _handle_transform(self, node, ctx):
        script = node.config.get("script", "")
        local_scope = {"ctx": ctx, "result": None}
        exec_globals = {"__builtins__": {}}
        try:
            exec(script, exec_globals, local_scope)
        except Exception as e:
            return {"error": str(e), "executed": False}
        return {"executed": True, "result": local_scope.get("result")}

    def _handle_delay(self, node, ctx):
        seconds = node.config.get("seconds", 1)
        time.sleep(seconds)
        return {"delayed": True, "seconds": seconds}

    def _handle_merge(self, node, ctx):
        all_outputs = list(ctx.get("node_outputs", {}).values())
        merged = {}
        for output in all_outputs:
            if isinstance(output, dict):
                for k, v in output.items():
                    if k not in merged:
                        merged[k] = v
                    elif isinstance(merged[k], list) and isinstance(v, list):
                        merged[k].extend(v)
        return {"merged": True, "output": merged}

    def _handle_loop(self, node, ctx):
        return {"looped": True, "config": node.config}

    def _handle_end(self, node, ctx):
        return {"ended": True}
