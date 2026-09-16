"""runs and generates the graphical images and sends to discord webhooks"""

import subprocess
import shutil
import os
import json
from server.storage import MODS_DIR

GRAPHICS_DIR = MODS_DIR / "tournament" / "graphics"

def run(data: dict) -> None:
    """runs the script"""
    uv = shutil.which("uv")

    # run the generation script using uv
    script_path = str(GRAPHICS_DIR / "generator.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = MODS_DIR
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.Popen([uv, "run", script_path, json.dumps(data)], env=env)
