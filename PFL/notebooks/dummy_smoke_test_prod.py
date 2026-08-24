

dbutils.widgets.text("environment", "prod")
env = dbutils.widgets.get("environment")


print(f"[dummy_smoke_test_prod] Running in '{env}' target - PROD workspace.")
print("[dummy_smoke_test_prod] L2 merge review + L3 manual approval both passed to get here.")
print("[dummy_smoke_test_prod] HOTFIX PFL-0000 applied - emergency third sanity check added.")

result = 1 + 1
assert result == 2, "Prod smoke test failed basic sanity check"

second_check = 2 * 3
assert second_check == 6, "Prod smoke test failed second sanity check"

third_check = 3 * 3
assert third_check == 9, "Prod smoke test failed hotfix sanity check"

print("[dummy_smoke_test_prod] Prod smoke test passed. No real catalogue data touched.")
