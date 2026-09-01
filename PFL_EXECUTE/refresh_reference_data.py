# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"[{env}] Stuti is execute file ran successfully")