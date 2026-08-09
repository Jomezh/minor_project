from config import INITIAL_ADMIN_UID, Tier
from database.database import Database
from core.access_policy import AccessPolicy


db = Database()
policy = AccessPolicy(db)

admin_uid = db.normalize_uid(INITIAL_ADMIN_UID)

print("Seeded admin:", db.get_card(admin_uid)["label"])
print("Admin check:", policy.is_admin(admin_uid))

decision = policy.evaluate_normal_access(admin_uid)

print("Access allowed:", decision.allowed)
print("Result:", decision.result.value)
print("Reason:", decision.reason)

guest_id = db.create_card(
    uid="AA-BB-CC-DD",
    label="Guest 01",
    tier=Tier.GUEST,
    created_by=admin_uid,
    valid_until="2099-12-31T23:59:59+00:00",
)

print("Created guest card ID:", guest_id)

guest_decision = policy.evaluate_normal_access("AA-BB-CC-DD")

print("Guest allowed:", guest_decision.allowed)
print("Guest result:", guest_decision.result.value)
print("Guest reason:", guest_decision.reason)

db.close()
