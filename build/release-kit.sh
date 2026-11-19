#!/bin/sh
# Maintainers: build/build.sh first. Use bsdiff4 1.2.6 to encode the ASAR delta.
set -eu
[ "$#" -eq 3 ] || { echo 'Usage: release-kit.sh SIGNED_VENDOR.app REBUILT.app NEW_OUTPUT.tar.gz' >&2; exit 2; }
export COPYFILE_DISABLE=1
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
base="$1/Contents/Resources/app.asar"
modified="$2/Contents/Resources/app.asar"
[ ! -e "$3" ] || { echo 'Output exists' >&2; exit 1; }
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for f in download.py model-files.txt serve.py service.py verify.py host.sb omlx-server.sb; do
    cp "$root/macos/$f" "$work/$f"
done
cp "$root/LICENSE" "$work/LICENSE"
cp "$root/build/node_modules/mime/LICENSE" "$work/mime-LICENSE"
bsdiff4 "$base" "$modified" "$work/local-desktop.bsdiff"
bspatch "$base" "$work/roundtrip" "$work/local-desktop.bsdiff"
cmp "$work/roundtrip" "$modified"
chmod 644 "$work"/*
TZ=UTC touch -t 202601010000 "$work"/*
tar --format ustar --uid 0 --gid 0 --uname root --gname wheel -czf "$3" -C "$work" LICENSE mime-LICENSE download.py model-files.txt serve.py service.py verify.py host.sb omlx-server.sb local-desktop.bsdiff
shasum -a 256 "$3" "$modified"
/usr/libexec/PlistBuddy -c 'Print :ElectronAsarIntegrity:Resources/app.asar:hash' "$2/Contents/Info.plist"
