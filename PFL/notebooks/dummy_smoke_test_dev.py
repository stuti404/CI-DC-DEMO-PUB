# Databricks notebook source

# Dummy smoke test - DEV branch.

# Push straight to `dev` (or merge feature/* -> dev). Auto-deploys, no manual

# gate (Doc Sec 2.1/6). Only Level 1 review applies, done before merge.

#

# Back-merged from hotfix PFL-0000 (Doc Sec 10.1) - keeps dev in sync with

# the emergency fix that went straight to main.



# COMMAND ----------



dbutils.widgets.text("environment", "dev")

env = dbutils.widgets.get("environment")



# COMMAND ----------



print(f"[dummy_smoke_test_dev] Running in '{env}' target - BU dev workspace.")

print("[dummy_smoke_test_dev] No manual approval expected before this ran.")

print("[dummy_smoke_test_dev] Back-merged hotfix PFL-0000 - emergency third sanity check added.")



result = 1 + 1

assert result == 2, "Dev smoke test failed basic sanity check"



second_check = 2 * 3

assert second_check == 6, "Dev smoke test failed second sanity check"



third_check = 3 * 3

assert third_check == 9, "Dev smoke test failed hotfix sanity check"



print("[dummy_smoke_test_dev] Dev smoke test passed.")
