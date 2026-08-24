# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")

result = 1 + 10
assert result == 11

second_check = 2 * 2
assert second_check == 4

print("Smoke test passed")
# feature work
