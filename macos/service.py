"""Register and verify the per-user local inference service."""
import json
import os
import plistlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from serve import INFERENCE, PROFILE, PYTHON_HOME, RESOURCES

LABEL = "local.harness.offline.inference"
DOMAIN = f"gui/{os.getuid()}"
AGENT = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
CLIENT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def endpoint_ready():
    key = (INFERENCE / "inference.key").read_text().strip()
    request = urllib.request.Request("http://127.0.0.1:8000/v1/models",
                                     headers={"Authorization": "Bearer " + key})
    try:
        with CLIENT.open(request, timeout=3) as result:
            return any(m["id"] == "qwen/qwen3.8-27b" for m in json.load(result)["data"])
    except (OSError, KeyError, ValueError):
        return False


def main():
    executable = PYTHON_HOME / "bin/python3"
    launcher = Path(__file__).with_name("serve.py").resolve()
    cfg = {"Label": LABEL, "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False},
           "ThrottleInterval": 20,
           "ProgramArguments": [str(executable), str(launcher), "start"],
           "EnvironmentVariables": {"HOME": str(Path.home()), "PYTHONHOME": str(PYTHON_HOME),
                                    "PYTHONDONTWRITEBYTECODE": "1"},
           "StandardErrorPath": str(INFERENCE / "service.log")}
    if AGENT.exists() and plistlib.loads(AGENT.read_bytes()) != cfg:
        raise SystemExit(f"Another launch agent uses {AGENT}. Installation stopped.")
    running = subprocess.run(["launchctl", "print", DOMAIN + "/" + LABEL],
                             capture_output=True).returncode == 0
    if running and not AGENT.exists():
        raise SystemExit("Another launch agent already uses the service label.")
    if not running:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", 8000))
            except OSError:
                raise SystemExit("Local port 8000 is occupied. Free it and run the installer again.")
        AGENT.parent.mkdir(parents=True, exist_ok=True)
        if not AGENT.exists():
            with tempfile.NamedTemporaryFile(dir=AGENT.parent, delete=False) as tmp:
                plistlib.dump(cfg, tmp)
            os.replace(tmp.name, AGENT)
        subprocess.run(["launchctl", "bootstrap", DOMAIN, str(AGENT)], check=True)
    for _ in range(120):
        if endpoint_ready():
            return
        time.sleep(1)
    raise SystemExit(f"Inference is not ready. See {INFERENCE / 'service.log'}")


if __name__ == "__main__":
    main()
