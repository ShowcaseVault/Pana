import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
FE_DIR = ROOT / "Pana"

npm_cmd = "npm.cmd" if os.name == "nt" else "npm"

cmd = [
    npm_cmd,
    "run",
    "dev",
]

subprocess.run(
    cmd,
    cwd=FE_DIR,
    check=True
)
