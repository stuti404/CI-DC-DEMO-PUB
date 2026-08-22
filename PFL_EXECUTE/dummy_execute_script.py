# Dummy execute artefact for CI/CD pipeline validation.
# Anything under PFL_EXECUTE/ auto-generates an "execute" CI/CD artefact
# (Doc Sec 3). This script intentionally touches no real catalogue data -
# it only proves the execute pipeline can build and run the artefact.

import os
import sys


def main():
    target = os.environ.get("BUNDLE_TARGET", "dev")
    run_id = os.environ.get("CODEBUILD_BUILD_ID", "local")
    print(f"[dummy_execute_script] Executing against '{target}' target (dummy run, no real catalogue access).")
    print(f"[dummy_execute_script] CodeBuild run id: {run_id}")

    checks_passed = True
    if not checks_passed:
        print("[dummy_execute_script] Execute smoke test FAILED")
        sys.exit(1)

    print("[dummy_execute_script] Execute smoke test passed.")


if __name__ == "__main__":
    main()
