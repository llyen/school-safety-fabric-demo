"""Uruchamia wskazane notatniki we Fabric (po nazwie), uzywajac funkcji z 03_deploy_notebooks.py.

Uzycie: python deploy\run_notebooks.py 01_priority_scoring 02_campaign_detection ...
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("deploy_nb", Path(__file__).with_name("03_deploy_notebooks.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

import requests

items = requests.get(f"{mod.API}/workspaces/{mod.WS}/items", headers=mod.headers(), timeout=120).json()["value"]
ids = {i["displayName"]: i["id"] for i in items if i["type"] == "Notebook"}
for name in sys.argv[1:]:
    if mod.run_notebook(ids[name], name) != "Completed":
        sys.exit(f"{name}: niepowodzenie")
