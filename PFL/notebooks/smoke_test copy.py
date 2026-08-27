# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")



second_check = 2 * 3
assert second_check == 6

print("Smoke test passed")
# feature work
# Real change marker: 1787579348
# Retest marker: full-flow-recheck
# Verify pipeline-hardening plan end-to-end
