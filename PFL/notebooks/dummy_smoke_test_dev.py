# Databricks notebook source
# Dummy smoke test - DEV branch.
# Push straight to `dev` (or merge feature/* -> dev). Auto-deploys, no manual
# gate (Doc Sec 2.1/6). Only Level 1 review applies, done before merge.

# COMMAND ----------

dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"[dummy_smoke_test_dev] Running in '{env}' target - BU dev workspace.")
print("[dummy_smoke_test_dev] No manual approval expected before this ran.")

result = 1 + 1
assert result == 2, "Dev smoke test failed basic sanity check"

print("[dummy_smoke_test_dev] Dev smoke test passed.")

