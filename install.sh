#!/bin/bash
# Local Harness for macOS. Downloads are public. Inference stays on loopback.
set -euo pipefail
umask 077

die() { printf '%s\n' "$*" >&2; exit 1; }
sha() { /usr/bin/shasum -a 256 "$1" | /usr/bin/awk '{print $1}'; }
check() { [[ "$(sha "$1")" == "$2" ]] || die "Checksum mismatch: ${1##*/}"; }

download() {
    local url=$1 dest=$2 hash=$3
    if [[ ! -f "$dest" ]]; then
        printf 'Downloading %s\n' "${dest##*/}"
        /usr/bin/curl --fail --location --show-error --silent --retry 4 --connect-timeout 30 \
            --proto '=https' --proto-redir '=https' -C - -o "$dest.part" "$url"
        if [[ "$(sha "$dest.part")" != "$hash" ]]; then
            rm -f "$dest.part"
            die "Download failed verification. Run the installer again."
        fi
        mv "$dest.part" "$dest"
    fi
    check "$dest" "$hash"
}

cleanup() {
    if [[ -n "${mount:-}" ]] && /sbin/mount | grep -Fq " on $mount ("; then
        /usr/bin/hdiutil detach "$mount" -quiet || { rm -f "$lock"; return; }
    fi
    [[ -z "${work:-}" ]] || rm -rf "$work"
    rm -f "$lock"
}

runtime_cdhash() {
    /usr/bin/codesign -d --verbose=4 "$1" 2>&1 | /usr/bin/awk -F= '/^CDHash=/{print $2}'
}

install_runtime() {
    local name digest signature stamp="$profile/Runtime/omlx-0.8.0.cdhash"
    if [[ $major = 15 ]]; then
        name=oMLX-0.8.0-macos15-sequoia.dmg
        digest=e6aa1e73749b070a7509d7160ef65377e7d50b4ccc96b5b8f1687fd66e21f587
    else
        name=oMLX-0.8.0-macos26-27.dmg
        digest=e1025cd9b2e6eea5331adb66a3d042f546d9aaf1d0c79933ed99d4530348b428
    fi
    if [[ ! -e "$runtime" ]]; then
        download "https://github.com/jundot/omlx/releases/download/v0.8.0/$name" "$cache/$name" "$digest"
        mount="$work/mount"
        mkdir "$mount"
        /usr/bin/hdiutil attach "$cache/$name" -readonly -nobrowse -mountpoint "$mount" -quiet
        /usr/bin/ditto "$mount/oMLX.app" "$work/oMLX.app"
        /usr/bin/codesign --verify --deep --strict "$work/oMLX.app"
        signature=$(runtime_cdhash "$work/oMLX.app")
        [[ "$signature" =~ ^[a-f0-9]{40}$ ]] || die 'Cannot read the signed oMLX code hash.'
        printf '%s\n' "$digest $signature" > "$work/omlx.cdhash"
        /usr/bin/hdiutil detach "$mount" -quiet
        mv "$work/omlx.cdhash" "$stamp"
        mount=''
        mv "$work/oMLX.app" "$runtime"
    fi
    [[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$runtime/Contents/Info.plist")" == app.omlx ]] || die 'Unexpected oMLX identity.'
    [[ "$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$runtime/Contents/Info.plist")" == 0.8.0 ]] || die 'Unexpected oMLX version.'
    /usr/bin/codesign --verify --deep --strict "$runtime"
    [[ -f "$stamp" && "$(cat "$stamp")" == "$digest $(runtime_cdhash "$runtime")" ]] || die 'The installed oMLX runtime differs from the verified disk image.'
}

install_desktop() {
    local app="$HOME/Applications/Local Harness.app" staged="$work/Local Harness.app" res plist
    local archive_hash=0b2db9c3819a1e0ed2812163690a3375e729f798cef04cdad2b056ebe5f9efd0
    if [[ ! -e "$app" ]]; then
        download 'https://download.deepseek.com/dsh-desk/bin/mac-arm64/deepseek-harness-0.2.2-rc.5-mac-arm64.zip' \
            "$cache/desktop.zip" c169975831897ee0925dbc23a661893511eff29bf645a7842ae1c2d2b5d5b8a0
        /usr/bin/ditto -xk "$cache/desktop.zip" "$work/vendor"
        mv "$work/vendor/DeepSeek Harness.app" "$staged"
        /usr/bin/codesign --verify --deep --strict "$staged"
        /usr/bin/codesign --verify -R='anchor apple generic and certificate leaf[subject.OU] = "NAN929V4UM"' "$staged"
        res="$staged/Contents/Resources"; plist="$staged/Contents/Info.plist"
        /usr/bin/bspatch "$res/app.asar" "$work/new.asar" "$work/kit/local-desktop.bsdiff"
        check "$work/new.asar" "$archive_hash"
        mv "$work/new.asar" "$res/app.asar"
        cp "$work/kit/host.sb" "$res/local-host.sb"
        rm -f "$res/app-update.yml"
        /usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier local.harness.offline.desktop' "$plist"
        /usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName Local Harness' "$plist"
        /usr/libexec/PlistBuddy -c 'Delete :CFBundleURLTypes' "$plist"
        /usr/libexec/PlistBuddy -c 'Set :ElectronAsarIntegrity:Resources/app.asar:hash 779f80ca0a65b1e234d3458d1b2eba6868f18aa73e2545e2f7e271c4e1ffd3e9' "$plist"
        /usr/bin/codesign --force --sign - --preserve-metadata=entitlements "$staged"
        /usr/bin/codesign --verify --deep --strict "$staged"
        mkdir -p "$HOME/Applications"
        mv "$staged" "$app"
    fi
    check "$app/Contents/Resources/app.asar" "$archive_hash"
    /usr/bin/codesign --verify --deep --strict "$app"
}

main() {
    if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --modelscope ) ]]; then die 'Usage: install.sh [--modelscope]'; fi
    export PATH=/usr/bin:/bin:/usr/sbin:/sbin
    [[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || die 'Open Terminal on an Apple Silicon Mac (native arm64).'
    major=$(/usr/bin/sw_vers -productVersion | cut -d. -f1)
    case "$major" in 15|26|27) ;; *) die 'Supported macOS versions: 15, 26 and 27.' ;; esac
    [[ $(id -u) != 0 ]] || die 'Run as the logged-in user, without sudo.'
    profile="$HOME/Library/Application Support/Local Harness"
    cache="$profile/Downloads"
    runtime="$profile/Runtime/oMLX.app"
    mkdir -p "$cache" "$profile/Runtime"
    lock="$profile/install.lock"
    /usr/bin/shlock -p $$ -f "$lock" || die 'Another installation is in progress.'
    work=''; mount=''
    trap cleanup EXIT
    trap 'exit 130' HUP INT TERM
    work=$(mktemp -d "$profile/.install.XXXXXXXX")
    if ! launchctl print "gui/$(id -u)/local.harness.offline.inference" >/dev/null 2>&1 && /usr/sbin/lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
        die "Local port 8000 is already in use. Free it before installing."
    fi
    echo 'Local Harness: installing the desktop, local inference runtime and ~16 GB of model files.'
    download 'https://github.com/CarverXx/harness-local-macos/releases/download/v1.0.0/local-harness-kit.tar.gz' \
        "$cache/local-harness-kit-v1.0.0.tar.gz" 3cd84377bab9d9613b8fd9355d395e988fe5dfd03605b77481fd577977e4d8ba
    mkdir "$work/kit"
    /usr/bin/tar xzf "$cache/local-harness-kit-v1.0.0.tar.gz" -C "$work/kit"
    install_runtime
    install_desktop
    export PYTHONHOME="$runtime/Contents/Resources/Python/cpython-3.11" PYTHONDONTWRITEBYTECODE=1
    unset PYTHONPATH
    py="$PYTHONHOME/bin/python3"
    local launcher="$profile/Runtime/launcher-v1.0.0"
    if [[ ! -e "$launcher" ]]; then
        mkdir "$work/launcher"
        cp "$work/kit/"{download.py,model-files.txt,serve.py,service.py,verify.py,omlx-server.sb,host.sb} "$work/launcher/"
        mv "$work/launcher" "$launcher"
    fi
    for file in download.py model-files.txt serve.py service.py verify.py omlx-server.sb host.sb; do
        /usr/bin/cmp -s "$work/kit/$file" "$launcher/$file" || die "Installed helper differs: $file"
    done
    "$py" "$launcher/download.py" "$@"
    if [[ ! -d "$profile/Inference" ]]; then "$py" "$launcher/serve.py" init; fi
    "$py" "$launcher/service.py"
    "$py" "$launcher/verify.py"
    rm -f "$cache/desktop.zip" "$cache/oMLX-0.8.0-macos15-sequoia.dmg" "$cache/oMLX-0.8.0-macos26-27.dmg"
    echo 'Ready. In Finder, choose Go > Home > Applications and open Local Harness.'
}
main "$@"
