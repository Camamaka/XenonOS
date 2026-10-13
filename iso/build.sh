#!/bin/bash
# XenonOS ISO olusturucu (WSL / Ubuntu icinde calistir)
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

SRC="/mnt/d/XenonOS/$ISO"   # NVMe'ye indirilmis ISO (Windows D:)
if [ -f "$SRC" ]; then
    ISO="$SRC"
elif [ ! -f "$ISO" ]; then
    echo ">> Ubuntu Server ISO indiriliyor (~2.7 GB)..."
    curl -L -o "$ISO" "$URL/$ISO"
fi

echo ">> Sha256 kontrol ediliyor..."
EXPECTED=$(curl -sL "$URL/SHA256SUMS" | grep "$(basename "$ISO")" | cut -d' ' -f1)
echo "$EXPECTED  $ISO" | sha256sum -c -

echo ">> XenonOS ISO'su olusturuluyor..."
rm -f XenonOS.iso
xorriso -indev "$ISO" -outdev XenonOS.iso \
    -map "$HERE/grub.cfg"  /boot/grub/grub.cfg \
    -map "$HERE/autoinstall.yaml" /autoinstall.yaml \
    -volid "XENONOS" \
    -boot_image any replay \
    -commit

cp XenonOS.iso "$HERE/XenonOS.iso"
echo ">> Hazir: $HERE/XenonOS.iso"
