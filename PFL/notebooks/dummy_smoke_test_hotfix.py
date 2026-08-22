# Databricks notebook source
# Dummy smoke test - HOTFIX branch.
# hotfix/<ticket>-<short-desc> -> PR straight to main (fast-track L1 + L2,
# Doc Sec 2.1). No direct pushes allowed; buildspec-validate must still pass.
# After merge, back-merge (or cherry-pick) this same commit into uat and dev
# the SAME day, and confirm buildspec-validate passes on both (Doc Sec 10.1).

# COMMAND ----------

dbutils.widgets.text("environment", "prod")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"[dummy_smoke_test_hotfix] Running in '{env}' target - emergency fix path.")
print("[dummy_smoke_test_hotfix] Reminder: back-merge into uat + dev today, record commit hash in the ticket.")
print("[dummy_smoke_test_hotfix] Back-merge tracked until closed - see PFL-0000 ticket.")

result = 1 + 1
assert result == 2, "Hotfix smoke test failed basic sanity check"

second_check = 2 * 3
assert second_check == 6, "Hotfix smoke test failed second sanity check"

print("[dummy_smoke_test_hotfix] Hotfix smoke test passed.")
