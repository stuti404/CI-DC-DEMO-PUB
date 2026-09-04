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
print("Testing the flow end to end")
print("verify direct-api live run")
print("verify json-output fix live")
print("verify run-now positional fix live")
print("verify service principal auth live")
print("verify git-source jobs live")