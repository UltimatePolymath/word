from typing import Optional

# Role hierarchy
ROLE_HIERARCHY = {
    "superuser": 3,
    "owner": 2,
    "sudo": 1,
    "uploader": 0
}

SUPERUSER_ID = 6783092268  # Hardcoded superuser ID

def can_manage_role(caller_role: Optional[str], target_role: str) -> bool:
    """Check if the caller can manage the target role based on hierarchy."""
    if caller_role is None:
        return False
    if caller_role == "superuser":
        return True
    caller_level = ROLE_HIERARCHY.get(caller_role, -1)
    target_level = ROLE_HIERARCHY.get(target_role, -1)
    return caller_level > target_level

def get_allowed_actions(caller_role: Optional[str]) -> list[str]:
    """Return the roles a caller can assign/revoke based on their role."""
    if caller_role is None:
        return []
    if caller_role == "superuser":
        return ["owner", "sudo", "uploader"]
    if caller_role == "owner":
        return ["sudo", "uploader"]
    if caller_role == "sudo":
        return ["uploader"]
    return []
