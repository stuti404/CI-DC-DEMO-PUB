import os
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_PATH = os.path.join(REPO_ROOT, "PFL", "notebook_pipeline.yml")
NOTEBOOKS_DIR = os.path.join(REPO_ROOT, "PFL", "notebooks")
OUTPUT_PATH = os.path.join(REPO_ROOT, "PFL", "resources", "dummy_job.yml")

TEMPLATE = """resources:
  jobs:
    {job_key}:
      name: "[${{bundle.target}}] {job_name}"
      max_concurrent_runs: 1
      tags:
        managed_by: databricks-asset-bundle
        pipeline: pfl-cicd-demo
        generated_by: generate_notebook_job.py

      schedule:
        quartz_cron_expression: "0 0 6 * * ?"
        timezone_id: "UTC"
        pause_status: PAUSED

      tasks:
{tasks_yaml}
"""

TASK_TEMPLATE = """        - task_key: {task_key}
{depends_on_yaml}          notebook_task:
            notebook_path: ../notebooks/{notebook}
            base_parameters:
              environment: ${{bundle.target}}
"""


def load_manifest():
    with open(MANIFEST_PATH) as f:
        manifest = yaml.safe_load(f)

    if not manifest.get("job_key"):
        sys.exit(f"{MANIFEST_PATH}: missing required 'job_key'")
    if not manifest.get("tasks"):
        sys.exit(f"{MANIFEST_PATH}: missing required 'tasks' (must be non-empty)")

    return manifest


def validate(manifest):
    task_keys = set()
    for task in manifest["tasks"]:
        for field in ("task_key", "notebook"):
            if not task.get(field):
                sys.exit(f"Task {task} is missing required field '{field}'")
        if task["task_key"] in task_keys:
            sys.exit(f"Duplicate task_key: {task['task_key']}")
        task_keys.add(task["task_key"])

        notebook_path = os.path.join(NOTEBOOKS_DIR, task["notebook"])
        if not os.path.isfile(notebook_path):
            sys.exit(f"Task '{task['task_key']}' references notebook '{task['notebook']}', "
                      f"which doesn't exist under PFL/notebooks/")

    for task in manifest["tasks"]:
        for dep in task.get("depends_on", []):
            if dep not in task_keys:
                sys.exit(f"Task '{task['task_key']}' depends_on unknown task_key '{dep}'")

    referenced = {task["notebook"] for task in manifest["tasks"]}
    on_disk = {f for f in os.listdir(NOTEBOOKS_DIR) if f.endswith(".py")}
    unregistered = sorted(on_disk - referenced)
    if unregistered:
        print(f"WARNING: these .py notebooks exist under PFL/notebooks/ but aren't in "
              f"{os.path.basename(MANIFEST_PATH)}, so they won't run: {unregistered}")


def render_tasks(tasks):
    rendered = []
    for task in tasks:
        depends_on = task.get("depends_on", [])
        if depends_on:
            depends_yaml = "          depends_on:\n" + "".join(
                f"            - task_key: {dep}\n" for dep in depends_on
            )
        else:
            depends_yaml = ""
        rendered.append(TASK_TEMPLATE.format(
            task_key=task["task_key"],
            depends_on_yaml=depends_yaml,
            notebook=task["notebook"],
        ))
    return "\n".join(rendered)


def main():
    manifest = load_manifest()
    validate(manifest)

    output = TEMPLATE.format(
        job_key=manifest["job_key"],
        job_name=manifest.get("job_name", manifest["job_key"]),
        tasks_yaml=render_tasks(manifest["tasks"]),
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(output)

    print(f"Generated {OUTPUT_PATH} from {len(manifest['tasks'])} task(s) in {os.path.basename(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
