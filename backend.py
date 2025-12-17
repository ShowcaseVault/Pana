import subprocess
from pathlib import Path

ROOT = Path(__file__).parent

subprocess.run(
    ["python", "-m", "api.server"],
    cwd=ROOT,
    check=True,
)
