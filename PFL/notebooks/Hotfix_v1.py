# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"Running smoke test in '{env}'")

a = 33
b = 44

temp = 546

print("Stuti test passed")
print("Smoke test passed")
