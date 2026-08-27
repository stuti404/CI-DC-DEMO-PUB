# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")

result = 1 + 23
assert result == 24
temp = 10
print(temp*3)
second_check = 2 * 5
assert second_check == 10

print("Smoke test passed")
# feature work
# Real change marker: 1787579348
# Retest marker: full-flow-recheck
# Verify pipeline-hardening plan end-to-end
