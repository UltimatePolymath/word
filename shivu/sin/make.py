from shivu.sin.currency import currency_plugs

async def initialize_user(user_id: int):
    """
    Triggers all plugin-specific user initialization functions
    if the user is not already initialized.
    """
    for plug in currency_plugs:
        ensure = getattr(plug, "ensure_user", None)
        is_initialized = getattr(plug, "is_user_initialized", None)

        if callable(ensure):
            try:
                if callable(is_initialized):
                    already_initialized = await is_initialized(user_id)
                    if already_initialized:
                        continue  # Skip this plugin if already initialized

                await ensure(user_id)
            except Exception as e:
                print(f"[!] Failed to initialize user in {plug.__name__}: {e}")
