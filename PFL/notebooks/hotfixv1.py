# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")

result = 1 + 21
assert result == 22

second_check = 2 * 21
assert second_check == 42

print("Smoke test passed")
# feature work
