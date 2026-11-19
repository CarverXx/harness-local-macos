"""Provision or run the dedicated loopback oMLX service on Apple Silicon."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile

PROFILE = Path.home() / "Library/Application Support/Local Harness"
INFERENCE = PROFILE / "Inference"
MODEL = "Qwen3.8-27B-4bit"
POLICY = Path(__file__).with_name("omlx-server.sb")
BUNDLED = PROFILE / "Runtime/oMLX.app"
RESOURCES = (BUNDLED if BUNDLED.is_dir() else Path("/Applications/oMLX.app")) / "Contents/Resources"
PYTHON_HOME = RESOURCES / "Python/cpython-3.11"


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def initialize(models):
    if not (models / MODEL / "model.safetensors.index.json").is_file():
        raise SystemExit(f"Place the pinned model in {models / MODEL} first.")
    if INFERENCE.exists():
        raise SystemExit("The inference profile already exists. Its credentials were preserved.")
    PROFILE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(dir=PROFILE) as work:
        staged = Path(work) / "Inference"
        staged.mkdir(mode=0o700)
        inference_key = secrets.token_urlsafe(36)
        (staged / "inference.key").write_text(inference_key + "\n", encoding="utf-8")
        shutil.copyfile(POLICY, staged / "server.sb")
        save_json(staged / "settings.json", {
            "version": "1.0",
            "server": {"host": "127.0.0.1", "port": 8000, "auto_start_on_launch": False,
                       "distributed_inference_enabled": False,
                       "cors_origins": ["http://127.0.0.1:8000", "http://localhost:8000"]},
            "model": {"model_dirs": [str(models)]},
            "auth": {"api_key": secrets.token_urlsafe(36), "secret_key": secrets.token_urlsafe(48),
                     "skip_api_key_verification": False, "allow_unauthenticated_inference": False,
                     "sub_keys": [{"key": inference_key, "name": "Local Harness"}]},
            "cache": {"enabled": True, "ssd_cache_max_size": "24GB", "hot_cache_max_size": "4GB"},
            "huggingface": {"hf_cache_enabled": False}, "usage": {"usage_history": False},
        })
        save_json(staged / "model_settings.json", {
            "version": 2, "models": {MODEL: {"model_alias": "qwen/qwen3.8-27b", "is_default": True}},
        })
        staged.rename(INFERENCE)
    print("Local credentials and offline policy initialized.")


def serve():
    executable = PYTHON_HOME / "bin/python3"
    if not executable.is_file() or not (INFERENCE / "inference.key").is_file():
        raise SystemExit("Install oMLX 0.8.0 and run the init command first.")
    policy = INFERENCE / "server.sb"
    if policy.read_bytes() != POLICY.read_bytes():
        raise SystemExit("Installed inference policy differs from the reviewed source.")
    env = {"HOME": str(Path.home()), "PATH": "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
           "PYTHONHOME": str(PYTHON_HOME), "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONPATH": os.pathsep.join(map(str, [RESOURCES, RESOURCES / "Python/framework-mlx-base/lib/python3.11/site-packages"])),
           "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1", "TRANSFORMERS_OFFLINE": "1",
           "MallocSpaceEfficient": "1"}
    os.chdir(INFERENCE)
    os.execve("/usr/bin/sandbox-exec", ["sandbox-exec", "-f", str(policy), str(executable),
              "-m", "omlx.cli", "serve", "--base-path", str(INFERENCE),
              "--host", "127.0.0.1", "--port", "8000"], env)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--models-dir", type=Path, default=PROFILE / "Models")
    commands.add_parser("start")
    args = parser.parse_args()
    os.umask(0o077)
    if args.command == "init":
        initialize(args.models_dir.expanduser().resolve())
    else:
        serve()
