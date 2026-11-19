"""Fetch pinned public weights in restartable ranges. Only verified files become visible."""
import argparse
import concurrent.futures
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile

from serve import MODEL, PROFILE

BASE = "https://huggingface.co/lmstudio-community/Qwen3.8-27B-MLX-4bit/resolve/6067b15cf581666a4aecf6af3afaba4bb5efc20c/"
MODELSCOPE = "https://www.modelscope.cn/models/lmstudio-community/Qwen3.8-27B-MLX-4bit/resolve/master/"
CHUNK = 32 * 1024 * 1024


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(url, parts, index, size):
    start = index * CHUNK
    end = min(start + CHUNK, size) - 1
    target = parts / str(index)
    if target.is_file() and target.stat().st_size == end - start + 1:
        return target
    partial = target.with_suffix(".tmp")
    subprocess.run(["/usr/bin/curl", "--fail", "--location", "--silent", "--show-error",
                    "--proto", "=https", "--proto-redir", "=https", "--retry", "4",
                    "--connect-timeout", "30", "--speed-limit", "1024", "--speed-time", "90",
                    "--max-filesize", str(end - start + 1), "--range", f"{start}-{end}",
                    "--output", str(partial), f"{url}?range_start={start}"], check=True)
    if partial.stat().st_size != end - start + 1:
        raise RuntimeError("Incomplete download. Run the installer again.")
    partial.replace(target)
    return target


def download(url, target, cache, size, sha):
    if target.exists():
        if target.stat().st_size == size and digest(target) == sha:
            return
        raise RuntimeError(f"Existing file differs from the release: {target}")
    parts = cache / sha
    parts.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    count = (size + CHUNK - 1) // CHUNK
    print(f"Downloading {target.name} ({size / 1e9:.2f} GB)", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        chunks = list(pool.map(lambda i: fetch(url, parts, i, size), range(count)))
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
        staged = Path(output.name)
        try:
            for chunk in chunks:
                with chunk.open("rb") as stream:
                    shutil.copyfileobj(stream, output, 1024 * 1024)
            output.close()
            if digest(staged) != sha:
                shutil.rmtree(parts)
                raise RuntimeError("Checksum mismatch. Run the installer to fetch a fresh copy.")
            staged.replace(target)
        finally:
            staged.unlink(missing_ok=True)
    shutil.rmtree(parts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--modelscope", action="store_true", help="Fetch the public mirror; verify the same pinned SHA-256 values.")
    source = MODELSCOPE if parser.parse_args().modelscope else BASE
    for line in Path(__file__).with_name("model-files.txt").read_text().splitlines():
        checksum, length, name = line.split()
        download(source + name, PROFILE / "Models" / MODEL / name,
                 PROFILE / "Downloads", int(length), checksum)
