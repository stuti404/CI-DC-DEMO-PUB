# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")

result = 1 + 1
assert result == 2

second_check = 2 * 3
assert second_check == 6

print("Smoke test passed")
# feature branch test edit
