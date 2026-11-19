#!/bin/sh
set -eu
if [ "$#" -ne 3 ]; then
  echo 'Usage: build/build.sh UPSTREAM_CHECKOUT NEW_OUTPUT.app SIGNED_UPSTREAM.app' >&2
  exit 2
fi
project=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
upstream=$(CDPATH= cd -- "$1" && pwd -P)
base=9c2670d3bce5275e0d1610272958121af87787bb
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
trap 'exit 1' HUP INT TERM
# Read named paths from a public Git object. Never copy the checkout's working tree.
git -C "$upstream" archive --format=tar -o "$work/source.tar" "$base" -- \
    apps/desktop/src apps/desktop/package.json packages/util/file-drag/src \
    packages/bundle/base/cordis.patch.yml packages/bundle/web-app/cordis.patch.yml tsconfig.client.json
mkdir "$work/src"
tar -xf "$work/source.tar" -C "$work/src"
(cd "$work/src" && git apply --check "$project/patches/local-desktop.patch" && git apply "$project/patches/local-desktop.patch")
LOCAL_HARNESS_UPSTREAM="$upstream" node "$project/build/build.mjs" "$work/src" "$2" "$3"
