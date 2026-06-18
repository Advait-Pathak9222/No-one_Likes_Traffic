"""Launch the ParkPulse Streamlit dashboard with stable local settings."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
STREAMLIT_BIN = PROJECT_DIR / ".deps" / "bin" / "streamlit"
APP_PATH = PROJECT_DIR / "app" / "streamlit_app.py"


def main() -> int:
    env = os.environ.copy()
    pythonpath_parts = [str(PROJECT_DIR / ".deps"), str(PROJECT_DIR)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / "outputs" / ".matplotlib"))
    env.setdefault("LOKY_MAX_CPU_COUNT", "4")
    env.setdefault("OMP_NUM_THREADS", "4")

    command = [
        str(STREAMLIT_BIN),
        "run",
        str(APP_PATH),
        "--global.developmentMode=false",
        "--server.address=localhost",
        "--server.port=8501",
        "--server.headless=true",
    ]
    print("Starting ParkPulse dashboard...")
    print("Open: http://localhost:8501")
    return subprocess.call(command, cwd=PROJECT_DIR, env=env)


if __name__ == "__main__":
    raise SystemExit(main())

