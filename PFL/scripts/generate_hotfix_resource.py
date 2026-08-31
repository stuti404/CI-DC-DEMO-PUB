import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESOURCE_PATH = os.path.join(REPO_ROOT, "PFL", "resources", "hotfix_job.yml")

TEMPLATE = """resources:
  jobs:
    hotfix_job:
      name: "[${{bundle.target}}] hotfix-job"
      max_concurrent_runs: 1
      tags:
        managed_by: databricks-asset-bundle
        pipeline: pfl-cicd-demo
        generated_by: generate_hotfix_resource.py

      tasks:
{tasks_yaml}
"""

TASK_TEMPLATE = """        - task_key: {task_key}
          notebook_task:
            notebook_path: ../../PFL_EXECUTE/{filename}
            base_parameters:
              environment: ${{bundle.target}}
"""


def sanitize_task_key(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if re.match(r"^\d", name):
        name = f"t_{name}"
    return name.lower()


def find_changed_pfl_execute_files(before_sha, after_sha):
    if not before_sha or set(before_sha) == {"0"}:
        print("No usable 'before' SHA (first push on branch, or force-push) - skipping hotfix job generation.")
        return []

    try:
        diff = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AM", before_sha, after_sha, "--", "PFL_EXECUTE/"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"git diff failed ({e}) - skipping hotfix job generation.")
        return []

    changed = [os.path.basename(f) for f in diff.stdout.splitlines() if f.strip().endswith(".py")]

    if not changed:
        print("No added/modified PFL_EXECUTE/*.py file in this push - nothing to generate.")
    return changed


def build_tasks(filenames):
    tasks = []
    seen_keys = {}
    for filename in filenames:
        task_key = sanitize_task_key(filename)
        if task_key in seen_keys:
            sys.exit(
                f"Task key collision: '{filename}' and '{seen_keys[task_key]}' "
                f"both sanitize to '{task_key}'"
            )
        seen_keys[task_key] = filename
        tasks.append((task_key, filename))
    return tasks


def render_tasks(tasks):
    return "\n".join(
        TASK_TEMPLATE.format(task_key=task_key, filename=filename)
        for task_key, filename in tasks
    )


def main():
    before_sha = os.environ.get("BEFORE_SHA", "")
    after_sha = os.environ.get("AFTER_SHA", "")

    filenames = find_changed_pfl_execute_files(before_sha, after_sha)
    if not filenames:
        if os.path.exists(RESOURCE_PATH):
            os.remove(RESOURCE_PATH)
        return

    tasks = build_tasks(filenames)

    os.makedirs(os.path.dirname(RESOURCE_PATH), exist_ok=True)
    with open(RESOURCE_PATH, "w") as f:
        f.write(TEMPLATE.format(tasks_yaml=render_tasks(tasks)))

    print(f"Generated {RESOURCE_PATH} with {len(tasks)} task(s): {[t[0] for t in tasks]}")


if __name__ == "__main__":
    sys.exit(main())
