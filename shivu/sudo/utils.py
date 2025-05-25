from shivu.sudo.db import get_user_role

# Hardcoded Superuser ID
SUPERUSER_ID = 6783092268

# Role hierarchy
ROLES = ["superuser", "owner", "sudo", "uploader"]
RANK = {role: i for i, role in enumerate(ROLES)}

def get_rank(role: str) -> int:
    return RANK.get(role, 100)  # Unknown roles treated as lowest rank

def is_superuser(user_id: int) -> bool:
    return user_id == SUPERUSER_ID

async def get_effective_role(user_id: int) -> str:
    if is_superuser(user_id):
        return "superuser"
    return await get_user_role(user_id) or None

async def can_assign(assigner_id: int, target_role: str) -> bool:
    assigner_role = await get_effective_role(assigner_id)
    if assigner_role == "superuser":
        return True
    if assigner_role == "owner":
        return target_role in ["sudo", "uploader"]
    if assigner_role == "sudo":
        return target_role == "uploader"
    return False

async def can_revoke(revoker_id: int, target_role: str) -> bool:
    # Same logic as assigning
    return await can_assign(revoker_id, target_role)

async def can_modify(assigner_id: int, target_id: int) -> bool:
    # Prevent modifying someone at equal or higher level
    assigner_role = await get_effective_role(assigner_id)
    target_role = await get_effective_role(target_id)

    if assigner_role is None:
        return False
    if assigner_role == "superuser":
        return True
    if target_role is None:
        return True

    return get_rank(assigner_role) < get_rank(target_role)
