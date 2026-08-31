# Databricks notebook source
dbutils.widgets.text("environment", "dev")
env = dbutils.widgets.get("environment")

# COMMAND ----------

from datetime import datetime

run_started_at = datetime.utcnow().isoformat()
print(f"[{env}] refresh_reference_data started at {run_started_at}")

# COMMAND ----------

expected_tables = ["reference_currency", "reference_country", "reference_calendar"]
missing_tables = []

for table_name in expected_tables:
    exists = spark.catalog.tableExists(table_name)
    print(f"[{env}] checked '{table_name}': {'present' if exists else 'MISSING'}")
    if not exists:
        missing_tables.append(table_name)

# COMMAND ----------

if missing_tables:
    raise Exception(f"[{env}] refresh_reference_data failed: missing tables {missing_tables}")

print(f"[{env}] refresh_reference_data completed successfully - all {len(expected_tables)} reference tables present")
