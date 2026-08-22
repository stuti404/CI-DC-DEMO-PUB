# Databricks notebook source
# Dummy smoke test - UAT branch.
# PR from dev -> uat. Auto-deploys to UAT workspace, but requires QA/business
# validation before the follow-up PR to main can be opened (Doc Sec 2.1/6).

# COMMAND ----------

dbutils.widgets.text("environment", "uat")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"[dummy_smoke_test_uat] Running in '{env}' target - UAT workspace.")
print("[dummy_smoke_test_uat] Flag for QA/business validation before PR to main.")

result = 1 + 1
assert result == 2, "UAT smoke test failed basic sanity check"

second_check = 2 * 3
assert second_check == 6, "UAT smoke test failed second sanity check"

print("[dummy_smoke_test_uat] UAT smoke test passed - awaiting QA sign-off.")
