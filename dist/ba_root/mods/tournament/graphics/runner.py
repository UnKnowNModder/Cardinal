"""runs and generates the graphical images and sends to discord webhooks"""

import subprocess
import shutil
import os
import json
from server.storage import MODS_DIR

FILES = {
    "title.png": "https://files.catbox.moe/aw1utu.png",
    "logo.png": "https://files.catbox.moe/g92tad.png",
    "arial.ttf": "https://cdn.jsdelivr.net/gh/taveevut/Windows-10-Fonts-Default@master/arial.ttf",
    "arialbd.ttf": "https://cdn.jsdelivr.net/gh/taveevut/Windows-10-Fonts-Default@master/arialbd.ttf",
}

GRAPHICS_DIR = MODS_DIR / "tournament" / "graphics"


def download(url: str, path: str) -> bool:
    """downloads a file from a url to a path"""
    try:
        subprocess.run(["curl", "-fsSL", url, "-o", path], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def verify_dependencies() -> bool:
    """verifies that all dependencies are present"""
    download_statuses = []
    for file, url in FILES.items():
        file_path = GRAPHICS_DIR / file
        if not file_path.exists():
            download_statuses.append(download(url, str(file_path)))

    return all(download_statuses)


def run(data: dict) -> None:
    """runs the script"""
    if not verify_dependencies():
        print("Missing dependencies, or download failed.")
        return

    uv = shutil.which("uv")

    # check if Pillow is installed.
    try:
        import PIL
    except ImportError:
        # quietly install it.
        subprocess.run([uv, "add", "pillow"], check=True)

    # run the generation script using uv
    script_path = str(GRAPHICS_DIR / "generator.py")
    env = os.environ.copy()
    env["PYTHONPATH"] = MODS_DIR
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.Popen([uv, "run", script_path, json.dumps(data)], env=env)
