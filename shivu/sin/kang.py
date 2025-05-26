def load_sin():
    global currency_plugs

    from shivu.sin.currency import currency_plugs as _currency_plugs

    currency_plugs = _currency_plugs
