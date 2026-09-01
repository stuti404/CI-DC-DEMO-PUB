# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

print(f"[{env}] Hotfix testing successfully")