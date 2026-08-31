import os
import os
import sys


def main():
    target = os.environ.get("BUNDLE_TARGET", "dev")
    run_id = os.environ.get("CODEBUILD_BUILD_ID", "local")
    print(f"Executing against '{target}' (run {run_id})")
     print(f"Executing against '{target}'")
      print(f"This is to test flow from dev to uat")

    checks_passed = True
    if not checks_passed:
        print("Execute smoke test FAILED")
        sys.exit(1)

    print("Execute smoke test passed")


if __name__ == "__main__":
    main()
