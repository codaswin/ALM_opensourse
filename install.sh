#!/usr/bin/env bash
# One-line installer for AI LinkedIn Manager (Linux).
#
#   curl -fsSL https://raw.githubusercontent.com/codaswin/ALM_opensourse/main/install.sh | bash
#
# Downloads the latest GitHub Release and installs it with your system's
# native package manager (apt/.deb or dnf/.rpm), falling back to a
# standalone AppImage if neither is available. No cloning, no build tools,
# no Node/Rust/Python required on your machine.

set -euo pipefail

REPO="codaswin/ALM_opensourse"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

echo "Looking up the latest release of AI LinkedIn Manager..."
RELEASE_JSON="$(curl -fsSL "$API_URL")"

find_asset_url() {
    # Pulls the first browser_download_url whose asset name ends in $1,
    # without depending on jq being installed.
    echo "$RELEASE_JSON" \
        | grep -o "\"browser_download_url\": *\"[^\"]*${1}\"" \
        | head -n1 \
        | sed -E 's/.*"(https:[^"]+)"/\1/'
}

install_deb() {
    local url; url="$(find_asset_url '\.deb')"
    [ -n "$url" ] || return 1
    local tmp; tmp="$(mktemp --suffix=.deb)"
    echo "Downloading $url"
    curl -fsSL -o "$tmp" "$url"
    echo "Installing (requires sudo)..."
    sudo apt install -y "$tmp"
    rm -f "$tmp"
    echo "Done. Launch it from your applications menu, or run: ai-linkedin-manager"
}

install_rpm() {
    local url; url="$(find_asset_url '\.rpm')"
    [ -n "$url" ] || return 1
    local tmp; tmp="$(mktemp --suffix=.rpm)"
    echo "Downloading $url"
    curl -fsSL -o "$tmp" "$url"
    echo "Installing (requires sudo)..."
    sudo dnf install -y "$tmp"
    rm -f "$tmp"
    echo "Done. Launch it from your applications menu, or run: ai-linkedin-manager"
}

install_appimage() {
    local url; url="$(find_asset_url '\.AppImage')"
    [ -n "$url" ] || { echo "No AppImage asset found in the latest release." >&2; return 1; }
    local dest_dir="$HOME/.local/bin"
    mkdir -p "$dest_dir"
    local dest="$dest_dir/ai-linkedin-manager.AppImage"
    echo "Downloading $url"
    curl -fsSL -o "$dest" "$url"
    chmod +x "$dest"
    echo "Installed to $dest"
    case ":$PATH:" in
        *":$dest_dir:"*) echo "Run it with: ai-linkedin-manager.AppImage" ;;
        *) echo "Add $dest_dir to your PATH, or run it directly: $dest" ;;
    esac
}

if command -v apt >/dev/null 2>&1 && command -v dpkg >/dev/null 2>&1; then
    install_deb && exit 0
    echo "Falling back to AppImage..." >&2
elif command -v dnf >/dev/null 2>&1; then
    install_rpm && exit 0
    echo "Falling back to AppImage..." >&2
fi

install_appimage
