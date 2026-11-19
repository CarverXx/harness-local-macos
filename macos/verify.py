"""Check the installed local edition and its inherited macOS network policy."""
import errno
import json
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import urllib.request

APP = Path.home() / "Applications/Local Harness.app"
RESOURCES = APP / "Contents/Resources"
SOURCE_POLICY = Path(__file__).with_name("host.sb")
BLOCKED = {errno.EPERM, errno.EACCES}


def test_restricted_process():
    # TEST-NET destinations never carry application data. The kernel must deny the
    # connection immediately, even if there is no route or remote server.
    for host, port in [("192.0.2.1", 443), ("2001:db8::1", 443), ("127.0.0.1", 80), ("127.0.0.1", 1234)]:
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        with socket.socket(family) as probe:
            probe.settimeout(2)
            if probe.connect_ex((host, port)) not in BLOCKED:
                raise RuntimeError(f"Expected sandbox denial for {host} port {port}")
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    key_file = Path.home() / "Library/Application Support/Local Harness/Inference/inference.key"
    request = urllib.request.Request("http://127.0.0.1:8000/v1/models",
                                     headers={"Authorization": "Bearer " + key_file.read_text().strip()})
    with client.open(request, timeout=10) as response:
        models = json.load(response)["data"]
    if not any(model["id"] == "qwen/qwen3.8-27b" and model.get("owned_by") == "omlx" for model in models):
        raise RuntimeError("Configured local model is absent from oMLX")
    print("oMLX reachable, local model present, other IPv4/IPv6 connections denied")


def main():
    if sys.argv[1:] == ["--child"]:
        test_restricted_process()
        return
    policy = RESOURCES / "local-host.sb"
    if policy.read_bytes() != SOURCE_POLICY.read_bytes():
        raise RuntimeError("Installed policy differs from reviewed source")
    with (APP / "Contents/Info.plist").open("rb") as stream:
        manifest = plistlib.load(stream)
    if manifest["CFBundleIdentifier"] != "local.harness.offline.desktop":
        raise RuntimeError("Unexpected application identity")
    if (RESOURCES / "app-update.yml").exists():
        raise RuntimeError("Unexpected update feed")
    subprocess.run(["codesign", "--verify", "--deep", "--strict", APP], check=True)
    server_policy = Path.home() / "Library/Application Support/Local Harness/Inference/server.sb"
    if server_policy.read_bytes() != Path(__file__).with_name("omlx-server.sb").read_bytes():
        raise RuntimeError("Installed oMLX network policy differs from reviewed source")
    for network_policy in (policy, server_policy):
        subprocess.run(["/usr/bin/sandbox-exec", "-f", network_policy, sys.executable,
                        __file__, "--child"], check=True)
    key = (server_policy.parent / "inference.key").read_text().strip()
    request = urllib.request.Request(
        "http://127.0.0.1:8000/v1/chat/completions",
        data=json.dumps({"model": "qwen/qwen3.8-27b", "messages": [
            {"role": "user", "content": "Write the number 7."}
        ], "temperature": 0, "max_tokens": 16}).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    print("Testing the first local generation (the model may take a moment to load).", flush=True)
    with client.open(request, timeout=240) as response:
        result = json.load(response)
    if not result.get("choices") or result.get("usage", {}).get("completion_tokens", 0) < 1:
        raise RuntimeError("Local inference returned no generated tokens")
    print("Local model generation, desktop signature and network policies verified.")


if __name__ == "__main__":
    main()
