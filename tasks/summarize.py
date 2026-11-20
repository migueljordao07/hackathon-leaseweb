"""Compute planning counts and weighted DAG critical path; no product execution."""
from collections import Counter
from functools import lru_cache
from pathlib import Path

import board


def summarize(tasks):
    errors = board.validate(tasks)
    if errors:
        raise ValueError("\n".join(errors))
    by_id = {task["id"]: task for task in tasks}

    @lru_cache(None)
    def longest(task_id):
        task = by_id[task_id]
        minutes, chain = max((longest(ref) for ref in task["depends_on"]),
                             default=(0, ()))
        return minutes + int(task["estimate"][:-1]), chain + (task_id,)

    counts = Counter(task["workstream"] for task in tasks)
    for ws in board.HOMES:
        minutes = sum(int(t["estimate"][:-1]) for t in tasks if t["workstream"] == ws)
        print(f"{ws}: {counts[ws]} tasks, {minutes} estimated task-minutes")
    minutes, chain = max((longest(task_id) for task_id in by_id), default=(0, ()))
    print(f"Total: {len(tasks)} tasks")
    print(f"Weighted DAG critical path: {' -> '.join(chain)}")
    print(f"Critical path estimate: {minutes} minutes")
    print("Lower bound only: excludes review/claim/merge delays and same-executor serialization.")
    print("Estimates are not measurements or a promise to meet the freeze.")
    return minutes, chain


if __name__ == "__main__":
    summarize(board.load_tasks(Path(__file__).resolve().parent))
