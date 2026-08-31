import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTEBOOKS_DIR = os.path.join(REPO_ROOT, "PFL", "notebooks")
OUTPUT_PATH = os.path.join(REPO_ROOT, "PFL", "resources", "dummy_job.yml")

JOB_KEY = "dummy_cicd_smoke_test"
JOB_NAME = "dummy-cicd-smoke-test"

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
          notebook_task:
            notebook_path: ../notebooks/{notebook}
            base_parameters:
              environment: ${{bundle.target}}
"""


def sanitize_task_key(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if re.match(r"^\d", name):
        name = f"t_{name}"
    return name.lower()


def discover_notebooks():
    entries = sorted(os.listdir(NOTEBOOKS_DIR))
    notebooks = []
    for f in entries:
        if f.endswith(".py"):
            notebooks.append(f)
        elif f.endswith(".ipynb"):
            print(f"SKIPPED (not a .py Databricks notebook): {f}")
    return notebooks


def build_tasks(notebooks):
    tasks = []
    seen_keys = {}
    for notebook in notebooks:
        task_key = sanitize_task_key(notebook)
        if task_key in seen_keys:
            sys.exit(
                f"Task key collision: '{notebook}' and '{seen_keys[task_key]}' "
                f"both sanitize to '{task_key}'"
            )
        seen_keys[task_key] = notebook
        tasks.append((task_key, notebook))
    return tasks


def render_tasks(tasks):
    return "\n".join(
        TASK_TEMPLATE.format(task_key=task_key, notebook=notebook)
        for task_key, notebook in tasks
    )


def main():
    notebooks = discover_notebooks()
    if not notebooks:
        sys.exit(f"No .py notebooks found under {NOTEBOOKS_DIR}")

    tasks = build_tasks(notebooks)

    output = TEMPLATE.format(
        job_key=JOB_KEY,
        job_name=JOB_NAME,
        tasks_yaml=render_tasks(tasks),
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(output)

    print(f"Generated {OUTPUT_PATH} with {len(tasks)} task(s): {[t[0] for t in tasks]}")


if __name__ == "__main__":
    main()
