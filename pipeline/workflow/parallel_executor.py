import uuid
import copy
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


class ParallelExecutor:
    def __init__(self):
        self._execution_store: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._stats: dict[str, dict] = {}

    def execute_parallel(self, nodes: list[dict], context: dict, engine: 'WorkflowEngine' = None, max_concurrent: int = 5) -> dict:
        execution_id = f"pe_{uuid.uuid4().hex[:12]}"
        total = len(nodes)
        results: dict[str, Any] = {}
        completed = 0
        failed = 0
        start_time = time.time()

        initial_context = copy.deepcopy(context)

        with self._lock:
            self._stats[execution_id] = {
                "execution_id": execution_id,
                "total_nodes": total,
                "completed": 0,
                "failed": 0,
                "in_progress": total,
                "started_at": datetime.utcnow().isoformat(),
                "nodes": {n.get("id", f"node_{i}"): {"status": "pending"} for i, n in enumerate(nodes)},
            }

        def execute_node(node: dict) -> tuple[str, Any]:
            node_id = node.get("id", f"node_{uuid.uuid4().hex[:8]}")
            node_context = copy.deepcopy(initial_context)
            node_context["_parallel_execution_id"] = execution_id
            node_context["_node_id"] = node_id
            try:
                handler = node.get("handler")
                if handler:
                    result = handler(node_context)
                elif engine:
                    result = engine.execute_node(node, node_context)
                else:
                    result = {"_executed": True, "node_id": node_id}
                with self._lock:
                    self._stats[execution_id]["completed"] += 1
                    self._stats[execution_id]["in_progress"] -= 1
                    self._stats[execution_id]["nodes"][node_id] = {"status": "completed"}
                return node_id, result
            except Exception as e:
                with self._lock:
                    self._stats[execution_id]["failed"] += 1
                    self._stats[execution_id]["in_progress"] -= 1
                    self._stats[execution_id]["nodes"][node_id] = {"status": "failed", "error": str(e)}
                return node_id, {"_error": str(e), "node_id": node_id}

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {executor.submit(execute_node, node): node for node in nodes}
            for future in as_completed(futures):
                node_id, result = future.result()
                results[node_id] = result

        end_time = time.time()
        duration = end_time - start_time

        with self._lock:
            self._stats[execution_id].update({
                "completed": completed,
                "failed": failed,
                "duration": round(duration, 3),
                "speedup": round(duration / max(0.001, (duration / max_concurrent)), 2) if max_concurrent > 1 else 1.0,
                "finished_at": datetime.utcnow().isoformat(),
            })

        return results

    def fan_out(self, node: dict, context: dict, split_key: str = "items") -> list[dict]:
        items = context.get(split_key, node.get("default_items", []))
        if not items and node.get("type") == "source":
            items = node.get("sample_data", [])

        if not items:
            return []

        split_strategy = node.get("split_strategy", "item_per_node")
        parallel_nodes = []

        if split_strategy == "item_per_node":
            for idx, item in enumerate(items):
                p_node = {
                    "id": f"{node.get('id', 'fanout')}_{idx}",
                    "type": node.get("child_type", "transform"),
                    "handler": node.get("handler"),
                    "input_item": item,
                    "index": idx,
                    "parent_id": node.get("id"),
                }
                parallel_nodes.append(p_node)

        elif split_strategy == "batch":
            batch_size = node.get("batch_size", 10)
            for batch_idx in range(0, len(items), batch_size):
                batch = items[batch_idx:batch_idx + batch_size]
                p_node = {
                    "id": f"{node.get('id', 'fanout')}_batch_{batch_idx // batch_size}",
                    "type": node.get("child_type", "transform"),
                    "handler": node.get("handler"),
                    "input_items": batch,
                    "batch_start": batch_idx,
                    "parent_id": node.get("id"),
                }
                parallel_nodes.append(p_node)

        elif split_strategy == "round_robin":
            num_partitions = node.get("num_partitions", 4)
            partitions = [[] for _ in range(num_partitions)]
            for idx, item in enumerate(items):
                partitions[idx % num_partitions].append(item)
            for pid, partition in enumerate(partitions):
                if partition:
                    p_node = {
                        "id": f"{node.get('id', 'fanout')}_rr_{pid}",
                        "type": node.get("child_type", "transform"),
                        "handler": node.get("handler"),
                        "input_items": partition,
                        "partition": pid,
                        "parent_id": node.get("id"),
                    }
                    parallel_nodes.append(p_node)

        return parallel_nodes

    def fan_in(self, node: dict, results: list[dict], merge_strategy: str = "collect") -> dict:
        if merge_strategy == "collect":
            collected = []
            for r in results:
                if isinstance(r, dict):
                    collected.append(r)
                elif isinstance(r, list):
                    collected.extend(r)
                else:
                    collected.append(r)
            return {"merged": collected, "count": len(collected), "merge_strategy": "collect"}

        elif merge_strategy == "merge":
            merged = {}
            for r in results:
                if isinstance(r, dict):
                    merged.update(r)
            return {"merged": merged, "count": len(merged), "merge_strategy": "merge"}

        elif merge_strategy == "join":
            parts = []
            separator = node.get("separator", "\n")
            for r in results:
                if isinstance(r, str):
                    parts.append(r)
                elif isinstance(r, dict):
                    parts.append(str(r))
            return {"merged": separator.join(parts), "count": len(parts), "merge_strategy": "join"}

        elif merge_strategy == "count":
            total = 0
            for r in results:
                if isinstance(r, (int, float)):
                    total += r
                elif isinstance(r, dict) and "count" in r:
                    total += r["count"]
                elif isinstance(r, list):
                    total += len(r)
            return {"merged": total, "count": total, "merge_strategy": "count"}

        else:
            return {"merged": results, "count": len(results), "merge_strategy": merge_strategy}

    def execute_map(self, items: list[Any], handler_fn: Callable, max_concurrent: int = 5) -> list[Any]:
        results = [None] * len(items)
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_map = {
                executor.submit(handler_fn, item, idx): idx for idx, item in enumerate(items)
            }
            for future in as_completed(future_map):
                idx = future_map[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = {"_error": str(e), "_index": idx}
        return results

    def execute_batch(self, nodes: list[dict], context: dict, batch_size: int = 10) -> list[dict]:
        batch_count = (len(nodes) + batch_size - 1) // batch_size
        all_results = []

        for batch_idx in range(batch_count):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(nodes))
            batch = nodes[start:end]

            batch_context = copy.deepcopy(context)
            batch_context["_batch_index"] = batch_idx
            batch_context["_batch_total"] = batch_count

            batch_results = self.execute_parallel(
                batch, batch_context, max_concurrent=batch_size
            )

            for node_id, result in batch_results.items():
                all_results.append({"node_id": node_id, "result": result, "batch": batch_idx})

            if batch_idx < batch_count - 1:
                inter_batch_delay = context.get("_batch_delay", 0)
                if inter_batch_delay > 0:
                    time.sleep(inter_batch_delay)

        return all_results

    def get_execution_stats(self, execution_id: str) -> dict:
        with self._lock:
            stats = self._stats.get(execution_id)
            if not stats:
                return {}
            node_statuses = list(stats.get("nodes", {}).values())
            completed_count = sum(1 for s in node_statuses if s.get("status") == "completed")
            failed_count = sum(1 for s in node_statuses if s.get("status") == "failed")
            in_progress_count = sum(1 for s in node_statuses if s.get("status") == "in_progress" or s.get("status") == "pending")

            result = {
                "execution_id": execution_id,
                "total_nodes": stats.get("total_nodes", 0),
                "completed": completed_count,
                "failed": failed_count,
                "in_progress": in_progress_count,
                "duration": stats.get("duration", 0),
                "speedup": stats.get("speedup", 1.0),
                "started_at": stats.get("started_at", ""),
                "finished_at": stats.get("finished_at", ""),
            }
            return result

    def clear_stats(self, execution_id: str = None):
        with self._lock:
            if execution_id:
                self._stats.pop(execution_id, None)
            else:
                self._stats.clear()
