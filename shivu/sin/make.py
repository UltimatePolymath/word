
from shivu.sin import currency_plugs

async def initialize_user(user_id: int):
    """
    Triggers all plugin-specific user initialization functions
    if the user is not already initialized.
    """
    for plug in currency_plugs:
        ensure = getattr(plug, "ensure_user", None)
        if callable(ensure):
            try:
                await ensure(user_id)
            except Exception as e:
                print(f"[!] Failed to initialize user in {plug.__name__}: {e}")
