import json
import os
import re
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GENERATED_DIR = os.path.join(REPO_ROOT, "PFL", "generated")

WORKSPACE_ROOT = {
    "dev": "/Shared/pfl-cicd/dev",
    "uat": "/Shared/pfl-cicd/uat",
    "prod": "/Shared/pfl-cicd/prod",
}


def sanitize_task_key(filename):
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if re.match(r"^\d", name):
        name = f"t_{name}"
    return name.lower()


def sanitize_branch(branch):
    name = re.sub(r"[^A-Za-z0-9_-]", "_", branch)
    return name[:60]


def get_changed_basenames(before_sha, after_sha, subdir, diff_filter="AM"):
    if not before_sha or set(before_sha) == {"0"}:
        print(f"No usable 'before' SHA (first push on branch, or force-push) - skipping {subdir} discovery.")
        return []

    try:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"--diff-filter={diff_filter}", before_sha, after_sha, "--", f"{subdir}/"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"git diff failed ({e}) - skipping {subdir} discovery.")
        return []

    return [os.path.basename(f) for f in diff.stdout.splitlines() if f.strip()]


def get_changed_files(before_sha, after_sha, subdir, diff_filter="AM"):
    all_touched = get_changed_basenames(before_sha, after_sha, subdir, diff_filter)
    changed = [f for f in all_touched if f.endswith(".py")]
    if not changed:
        print(f"No added/modified {subdir}/*.py file in this push.")
    return changed


def build_job_name(prefix):
    branch = os.environ.get("BRANCH_NAME", "unknown")
    sha = os.environ.get("COMMIT_SHA", "0000000")
    run_number = os.environ.get("RUN_NUMBER", "0")
    return f"{prefix}-{sanitize_branch(branch)}-{sha[:8]}-run{run_number}"


def build_job_spec(job_name, tasks, environment, generated_by):
    job_tasks = []
    for task in tasks:
        entry = {
            "task_key": task["task_key"],
            "notebook_task": {
                "notebook_path": task["notebook_path"],
                "base_parameters": {"environment": environment},
            },
        }
        if task.get("depends_on"):
            entry["depends_on"] = [{"task_key": key} for key in task["depends_on"]]
        job_tasks.append(entry)

    return {
        "name": job_name,
        "max_concurrent_runs": 1,
        "tags": {
            "managed_by": "direct-api",
            "pipeline": "pfl-cicd-demo",
            "environment": environment,
            "generated_by": generated_by,
        },
        "tasks": job_tasks,
    }


def write_job_json(path, spec):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(spec, f, indent=2)


def write_manifest(path, filenames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(filenames))


def clear_stale(path):
    if os.path.exists(path):
        os.remove(path)
