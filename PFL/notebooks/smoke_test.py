# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")

result = 1 + 23
assert result == 24

result = 1 + 2
assert result == 3

temp = 10
print(temp*3)
second_check = 2 * 5
assert second_check == 10

print("Smoke test passed")
print("Stuti is testing")

