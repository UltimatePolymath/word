
import importlib
import pathlib

currency_plugs = []

# Path to this folder
plugin_dir = pathlib.Path(__file__).parent

# Iterate through all .py files (excluding __init__.py)
for plugin_file in plugin_dir.glob("*.py"):
    if plugin_file.name == "__init__.py":
        continue

    module_name = f"shivu.sin.currency.{plugin_file.stem}"
    try:
        imported_module = importlib.import_module(module_name)
        currency_plugs.append(imported_module)
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")
