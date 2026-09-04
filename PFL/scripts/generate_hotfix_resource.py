import os
import re
import subprocess
import sys

import job_common

EXECUTE_SUBDIR = "PFL_EXECUTE"
OUTPUT_JSON = os.path.join(job_common.GENERATED_DIR, "hotfix_job.json")
OUTPUT_MANIFEST = os.path.join(job_common.GENERATED_DIR, "hotfix_files.txt")

NOTEBOOK_REFERENCE_RE = re.compile(r"PFL/notebooks/([A-Za-z0-9_\-]+\.py)")


def find_referenced_notebooks(after_sha, execute_filename):
    result = subprocess.run(
        ["git", "show", f"{after_sha}:{EXECUTE_SUBDIR}/{execute_filename}"],
        cwd=job_common.REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return sorted(set(NOTEBOOK_REFERENCE_RE.findall(result.stdout)))


def verify_notebook_exists(after_sha, notebook_filename):
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{after_sha}:PFL/notebooks/{notebook_filename}"],
        cwd=job_common.REPO_ROOT, capture_output=True, text=True,
    )
    return result.returncode == 0


def build_tasks(filenames, after_sha):
    tasks = []
    seen_keys = {}
    referenced_task_keys = {}

    def register(filename):
        task_key = job_common.sanitize_task_key(filename)
        if task_key in seen_keys and seen_keys[task_key] != filename:
            sys.exit(
                f"Task key collision: '{filename}' and '{seen_keys[task_key]}' "
                f"both sanitize to '{task_key}'"
            )
        seen_keys[task_key] = filename
        return task_key

    for filename in filenames:
        task_key = register(filename)
        depends_on = []

        for notebook in find_referenced_notebooks(after_sha, filename):
            if not verify_notebook_exists(after_sha, notebook):
                sys.exit(
                    f"'{filename}' references 'PFL/notebooks/{notebook}', "
                    f"but that file does not exist."
                )
            if notebook not in referenced_task_keys:
                notebook_key = register(notebook)
                referenced_task_keys[notebook] = notebook_key
                tasks.append({
                    "task_key": notebook_key,
                    "notebook_path": f"PFL/notebooks/{notebook}",
                })
            depends_on.append(referenced_task_keys[notebook])

        tasks.append({
            "task_key": task_key,
            "notebook_path": f"PFL_EXECUTE/{filename}",
            "depends_on": depends_on,
        })

    return tasks


def main():
    before_sha = os.environ.get("BEFORE_SHA", "")
    after_sha = os.environ.get("AFTER_SHA", "")
    environment = os.environ.get("ENVIRONMENT", "dev")

    filenames = job_common.get_changed_files(before_sha, after_sha, EXECUTE_SUBDIR, diff_filter="AM")

    if not filenames:
        job_common.clear_stale(OUTPUT_JSON)
        job_common.clear_stale(OUTPUT_MANIFEST)
        return

    tasks = build_tasks(filenames, after_sha)
    job_name = job_common.build_job_name("pfl-hotfix")
    spec = job_common.build_job_spec(job_name, tasks, environment, "generate_hotfix_resource.py", after_sha)

    job_common.write_job_json(OUTPUT_JSON, spec)
    job_common.write_manifest(OUTPUT_MANIFEST, filenames)

    print(f"Generated {OUTPUT_JSON} ('{job_name}') with {len(tasks)} task(s): {[t['task_key'] for t in tasks]}")


if __name__ == "__main__":
    sys.exit(main())
