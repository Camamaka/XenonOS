#!/bin/bash
# XenonOS ISO builder (run inside WSL / Ubuntu)
set -euo pipefail

VER="26.04.1"
ISO="ubuntu-${VER}-live-server-amd64.iso"
URL="https://releases.ubuntu.com/${VER}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HOME/xenonos-build"

mkdir -p "$WORK"
cd "$WORK"

sudo apt-get update
sudo apt-get install -y xorriso curl

SRC="/mnt/d/XenonOS/$ISO"   # ISO downloaded to the NVMe (Windows D:)
if [ -f "$SRC" ]; then
    ISO="$SRC"
elif [ ! -f "$ISO" ]; then
    echo ">> Downloading Ubuntu Server ISO (~2.7 GB)..."
    curl -L -o "$ISO" "$URL/$ISO"
fi

echo ">> Checking SHA256..."
EXPECTED=$(curl -sL "$URL/SHA256SUMS" | grep "$(basename "$ISO")" | cut -d' ' -f1)
echo "$EXPECTED  $ISO" | sha256sum -c -

echo ">> Building the XenonOS ISO..."
rm -f XenonOS.iso
xorriso -indev "$ISO" -outdev XenonOS.iso \
    -map "$HERE/grub.cfg"  /boot/grub/grub.cfg \
    -map "$HERE/autoinstall.yaml" /autoinstall.yaml \
    -volid "XENONOS" \
    -boot_image any replay \
    -commit

cp XenonOS.iso "$HERE/XenonOS.iso"
echo ">> Ready: $HERE/XenonOS.iso"
