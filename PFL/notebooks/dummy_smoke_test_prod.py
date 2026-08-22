# Databricks notebook source
# Dummy smoke test - PROD branch (main).
# PR uat -> main. Requires Level 2 review to merge, then CodePipeline's
# manual approval stage (Level 3, named prod release approver) before this
# ever reaches the prod workspace (Doc Sec 2.1/6).

# COMMAND ----------

dbutils.widgets.text("environment", "prod")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"[dummy_smoke_test_prod] Running in '{env}' target - PROD workspace.")
print("[dummy_smoke_test_prod] L2 merge review + L3 manual approval both passed to get here.")
print("[dummy_smoke_test_prod] HOTFIX PFL-0000 applied - emergency third sanity check added.")

result = 1 + 1
assert result == 2, "Prod smoke test failed basic sanity check"

second_check = 2 * 3
assert second_check == 6, "Prod smoke test failed second sanity check"

third_check = 3 * 3
assert third_check == 9, "Prod smoke test failed hotfix sanity check"

print("[dummy_smoke_test_prod] Prod smoke test passed. No real catalogue data touched.")
