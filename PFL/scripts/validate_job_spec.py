import json
import sys

path = sys.argv[1]
spec = json.load(open(path))

if "name" not in spec or "tasks" not in spec:
    sys.exit(f"{path} missing required keys")

for task in spec["tasks"]:
    if "task_key" not in task or "notebook_task" not in task or "notebook_path" not in task["notebook_task"]:
        sys.exit(f"{path} has a malformed task")

print(f"OK: {path}")
