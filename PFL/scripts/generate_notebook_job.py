import os
import sys

import job_common

NOTEBOOKS_SUBDIR = "PFL/notebooks"
OUTPUT_JSON = os.path.join(job_common.GENERATED_DIR, "notebook_job.json")
OUTPUT_MANIFEST = os.path.join(job_common.GENERATED_DIR, "notebook_files.txt")


def discover_changed_notebooks(before_sha, after_sha):
    all_touched = job_common.get_changed_basenames(before_sha, after_sha, NOTEBOOKS_SUBDIR, diff_filter="AM")

    for f in all_touched:
        if f.endswith(".ipynb"):
            print(f"SKIPPED (not a .py Databricks notebook): {f}")

    return [f for f in all_touched if f.endswith(".py")]


def build_tasks(notebooks, environment):
    tasks = []
    seen_keys = {}
    for notebook in notebooks:
        task_key = job_common.sanitize_task_key(notebook)
        if task_key in seen_keys:
            sys.exit(
                f"Task key collision: '{notebook}' and '{seen_keys[task_key]}' "
                f"both sanitize to '{task_key}'"
            )
        seen_keys[task_key] = notebook
        tasks.append({
            "task_key": task_key,
            "notebook_path": f"{job_common.WORKSPACE_ROOT[environment]}/notebooks/{notebook}",
        })
    return tasks


def main():
    before_sha = os.environ.get("BEFORE_SHA", "")
    after_sha = os.environ.get("AFTER_SHA", "")
    environment = os.environ.get("ENVIRONMENT", "dev")

    notebooks = discover_changed_notebooks(before_sha, after_sha)

    if not notebooks:
        job_common.clear_stale(OUTPUT_JSON)
        job_common.clear_stale(OUTPUT_MANIFEST)
        print("No changed PFL/notebooks/*.py files in this push - no notebook job to generate.")
        return

    tasks = build_tasks(notebooks, environment)
    job_name = job_common.build_job_name("pfl-notebooks")
    spec = job_common.build_job_spec(job_name, tasks, environment, "generate_notebook_job.py")

    job_common.write_job_json(OUTPUT_JSON, spec)
    job_common.write_manifest(OUTPUT_MANIFEST, notebooks)

    print(f"Generated {OUTPUT_JSON} ('{job_name}') with {len(tasks)} task(s): {[t['task_key'] for t in tasks]}")


if __name__ == "__main__":
    main()
