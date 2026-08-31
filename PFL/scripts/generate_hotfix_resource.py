"""Generate PFL/resources/hotfix_job.yml for whichever new file a hotfix added
under PFL_EXECUTE/, so it deploys and runs as a real Databricks job instead of
sitting inert. Not committed to git - the deploying CI job runs this right
before `databricks bundle deploy`, and bundle deploy reads the local working
tree, not just tracked files.

Uses the same before/after SHA range the pipeline's own artifact-packaging
step already diffs against (github.event.before / github.sha on a push
event), so this doesn't need to guess a commit ancestor across the
hotfix -> backport -> promotion chain.
"""
import os
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
        - task_key: run_hotfix_file
          notebook_task:
            notebook_path: ../../PFL_EXECUTE/{filename}
            base_parameters:
              environment: ${{bundle.target}}
"""


def find_new_pfl_execute_file(before_sha, after_sha):
    if not before_sha or set(before_sha) == {"0"}:
        print("No usable 'before' SHA (first push on branch, or force-push) - skipping hotfix job generation.")
        return None

    try:
        diff = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", before_sha, after_sha, "--", "PFL_EXECUTE/"],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"git diff failed ({e}) - skipping hotfix job generation.")
        return None

    added = [f for f in diff.stdout.splitlines() if f.strip().endswith(".py")]

    if not added:
        print("No new PFL_EXECUTE/*.py file in this push - nothing to generate.")
        return None
    if len(added) > 1:
        print(f"Expected at most one new PFL_EXECUTE file, found {len(added)}: {added} - skipping generation.")
        return None

    return os.path.basename(added[0])


def main():
    before_sha = os.environ.get("BEFORE_SHA", "")
    after_sha = os.environ.get("AFTER_SHA", "")

    filename = find_new_pfl_execute_file(before_sha, after_sha)
    if filename is None:
        if os.path.exists(RESOURCE_PATH):
            os.remove(RESOURCE_PATH)
        return

    os.makedirs(os.path.dirname(RESOURCE_PATH), exist_ok=True)
    with open(RESOURCE_PATH, "w") as f:
        f.write(TEMPLATE.format(filename=filename))

    print(f"Generated {RESOURCE_PATH} -> notebook_path ../../PFL_EXECUTE/{filename}")


if __name__ == "__main__":
    sys.exit(main())
